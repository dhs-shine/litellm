"""
This is a rate limiter implementation based on a similar one by Envoy proxy. 

This is currently in development and not yet ready for production.
"""
import os
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    Union,
    cast,
)

from fastapi import HTTPException

from litellm import DualCache
from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import UserAPIKeyAuth

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    from litellm.proxy.utils import InternalUsageCache as _InternalUsageCache
    from litellm.types.caching import RedisPipelineIncrementOperation

    Span = Union[_Span, Any]
    InternalUsageCache = _InternalUsageCache
else:
    Span = Any
    InternalUsageCache = Any

BATCH_RATE_LIMITER_SCRIPT = """
local results = {}
local now = tonumber(ARGV[1])
local window_size = tonumber(ARGV[2])

-- Process each window/counter pair
for i = 1, #KEYS, 2 do
    local window_key = KEYS[i]
    local counter_key = KEYS[i + 1]
    local increment_value = 1

    -- Check if window exists and is valid
    local window_start = redis.call('GET', window_key)
    if not window_start or (now - tonumber(window_start)) >= window_size then
        -- Reset window and counter
        redis.call('SET', window_key, tostring(now))
        redis.call('SET', counter_key, increment_value)
        redis.call('EXPIRE', window_key, window_size)
        redis.call('EXPIRE', counter_key, window_size)
        table.insert(results, tostring(now)) -- window_start
        table.insert(results, increment_value) -- counter
    else
        local counter = redis.call('INCR', counter_key)
        table.insert(results, window_start) -- window_start
        table.insert(results, counter) -- counter
    end
end

return results
"""

# Rate limit window sizes in seconds
WINDOW_SIZE_RPM = 60  # 1 minute
WINDOW_SIZE_RPH = 3600  # 1 hour
WINDOW_SIZE_RPD = 86400  # 1 day
WINDOW_SIZE_RPW = 604800  # 1 week
WINDOW_SIZE_RPMO = 2592000  # 1 month (30 days)


class RateLimitDescriptorRateLimitObject(TypedDict, total=False):
    requests_per_unit: Optional[int]
    tokens_per_unit: Optional[int]
    max_parallel_requests: Optional[int]
    window_size: Optional[int]


class RateLimitDescriptor(TypedDict):
    key: str
    value: str
    rate_limit: Optional[RateLimitDescriptorRateLimitObject]


class RateLimitStatus(TypedDict):
    code: str
    current_limit: int
    limit_remaining: int
    rate_limit_type: Literal["requests", "tokens", "max_parallel_requests"]
    descriptor_key: str


class RateLimitResponse(TypedDict):
    overall_code: str
    statuses: List[RateLimitStatus]


class RateLimitResponseWithDescriptors(TypedDict):
    descriptors: List[RateLimitDescriptor]
    response: RateLimitResponse


class _PROXY_MaxParallelRequestsHandler_v3(CustomLogger):
    def __init__(self, internal_usage_cache: InternalUsageCache):
        self.internal_usage_cache = internal_usage_cache
        if self.internal_usage_cache.dual_cache.redis_cache is not None:
            self.batch_rate_limiter_script = (
                self.internal_usage_cache.dual_cache.redis_cache.async_register_script(
                    BATCH_RATE_LIMITER_SCRIPT
                )
            )
        else:
            self.batch_rate_limiter_script = None

        self.window_size = int(os.getenv("LITELLM_RATE_LIMIT_WINDOW_SIZE", 60))

    async def in_memory_cache_sliding_window(
        self,
        keys: List[str],
        now_int: int,
        window_size: int,
    ) -> List[Any]:
        """
        Implement sliding window rate limiting logic using in-memory cache operations.
        This follows the same logic as the Redis Lua script but uses async cache operations.
        """
        results: List[Any] = []

        # Process each window/counter pair
        for i in range(0, len(keys), 2):
            window_key = keys[i]
            counter_key = keys[i + 1]
            increment_value = 1

            # Get the window start time
            window_start = await self.internal_usage_cache.async_get_cache(
                key=window_key,
                litellm_parent_otel_span=None,
                local_only=True,
            )

            # Check if window exists and is valid
            if window_start is None or (now_int - int(window_start)) >= window_size:
                # Reset window and counter
                await self.internal_usage_cache.async_set_cache(
                    key=window_key,
                    value=str(now_int),
                    ttl=window_size,
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
                await self.internal_usage_cache.async_set_cache(
                    key=counter_key,
                    value=increment_value,
                    ttl=window_size,
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
                results.append(str(now_int))  # window_start
                results.append(increment_value)  # counter
            else:
                # Increment the counter
                current_counter = await self.internal_usage_cache.async_get_cache(
                    key=counter_key,
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
                new_counter_value = (
                    int(current_counter) if current_counter is not None else 0
                ) + increment_value
                await self.internal_usage_cache.async_set_cache(
                    key=counter_key,
                    value=new_counter_value,
                    ttl=window_size,
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
                results.append(window_start)  # window_start
                results.append(new_counter_value)  # counter

        return results

    def create_rate_limit_keys(
        self,
        key: str,
        value: str,
        rate_limit_type: Literal["requests", "tokens", "max_parallel_requests"],
    ) -> str:
        """
        Create the rate limit keys for the given key and value.
        """
        counter_key = f"{{{key}:{value}}}:{rate_limit_type}"

        return counter_key

    def is_cache_list_over_limit(
        self,
        keys_to_fetch: List[str],
        cache_values: List[Any],
        key_metadata: Dict[str, Any],
    ) -> RateLimitResponse:
        """
        Check if the cache values are over the limit.
        """
        statuses: List[RateLimitStatus] = []
        overall_code = "OK"

        for i in range(0, len(cache_values), 2):
            item_code = "OK"
            window_key = keys_to_fetch[i]
            counter_key = keys_to_fetch[i + 1]
            counter_value = cache_values[i + 1]
            requests_limit = key_metadata[window_key]["requests_limit"]
            max_parallel_requests_limit = key_metadata[window_key][
                "max_parallel_requests_limit"
            ]
            tokens_limit = key_metadata[window_key]["tokens_limit"]

            # Determine which limit to use for current_limit and limit_remaining
            current_limit: Optional[int] = None
            rate_limit_type: Optional[
                Literal["requests", "tokens", "max_parallel_requests"]
            ] = None
            if counter_key.endswith(":requests"):
                current_limit = requests_limit
                rate_limit_type = "requests"
            elif counter_key.endswith(":max_parallel_requests"):
                current_limit = max_parallel_requests_limit
                rate_limit_type = "max_parallel_requests"
            elif counter_key.endswith(":tokens"):
                current_limit = tokens_limit
                rate_limit_type = "tokens"

            if (
                counter_key.endswith(":requests")
                and requests_limit is not None
                and counter_value is not None
                and int(counter_value) > requests_limit
            ):
                overall_code = "OVER_LIMIT"
                item_code = "OVER_LIMIT"
            elif (
                counter_key.endswith(":max_parallel_requests")
                and max_parallel_requests_limit is not None
                and counter_value is not None
                and int(counter_value) > max_parallel_requests_limit
            ):
                overall_code = "OVER_LIMIT"
                item_code = "OVER_LIMIT"
            elif (
                counter_key.endswith(":tokens")
                and tokens_limit is not None
                and counter_value is not None
                and int(counter_value) > tokens_limit
            ):
                overall_code = "OVER_LIMIT"
                item_code = "OVER_LIMIT"

            # Only compute limit_remaining if current_limit is not None
            limit_remaining = (
                current_limit - int(counter_value)
                if counter_value is not None
                else current_limit
            )

            statuses.append(
                {
                    "code": item_code,
                    "current_limit": current_limit,
                    "limit_remaining": limit_remaining,
                    "rate_limit_type": rate_limit_type,
                    "descriptor_key": key_metadata[window_key]["descriptor_key"],
                }
            )

        return RateLimitResponse(overall_code=overall_code, statuses=statuses)

    async def should_rate_limit(
        self,
        descriptors: List[RateLimitDescriptor],
        parent_otel_span: Optional[Span] = None,
        read_only: bool = False,
    ) -> RateLimitResponse:
        """
        Check if any of the rate limit descriptors should be rate limited.
        Returns a RateLimitResponse with the overall code and status for each descriptor.
        Uses batch operations for Redis to improve performance.
        """

        now = datetime.now().timestamp()
        now_int = int(now)  # Convert to integer for Redis Lua script

        # Group descriptors by window size
        rpm_descriptors = []
        rph_descriptors = []
        rpd_descriptors = []
        rpw_descriptors = []
        rpmo_descriptors = []

        for descriptor in descriptors:
            rate_limit = descriptor.get("rate_limit", {}) or {}
            window_size = rate_limit.get("window_size", WINDOW_SIZE_RPM)  # Default to 1 minute

            if window_size == WINDOW_SIZE_RPM:  # 1 minute window
                rpm_descriptors.append(descriptor)
            elif window_size == WINDOW_SIZE_RPH:  # 1 hour window
                rph_descriptors.append(descriptor)
            elif window_size == WINDOW_SIZE_RPD:  # 24 hour window
                rpd_descriptors.append(descriptor)
            elif window_size == WINDOW_SIZE_RPW:
                rpw_descriptors.append(descriptor)
            elif window_size == WINDOW_SIZE_RPMO:
                rpmo_descriptors.append(descriptor)

        # Process descriptors in order: rpm -> rph -> rpd
        all_statuses = []
        overall_code = "OK"

        # Process RPM limits first
        if rpm_descriptors:
            rpm_response = await self._process_rate_limits(
                descriptors=rpm_descriptors,
                now_int=now_int,
                window_size=WINDOW_SIZE_RPM,  # 1 minute
                parent_otel_span=parent_otel_span,
            )
            all_statuses.extend(rpm_response["statuses"])
            if rpm_response["overall_code"] == "OVER_LIMIT":
                overall_code = "OVER_LIMIT"
                return RateLimitResponse(overall_code=overall_code, statuses=all_statuses)

        # Process RPH limits if RPM passed
        if rph_descriptors:
            rph_response = await self._process_rate_limits(
                descriptors=rph_descriptors,
                now_int=now_int,
                window_size=WINDOW_SIZE_RPH,  # 1 hour
                parent_otel_span=parent_otel_span,
            )
            all_statuses.extend(rph_response["statuses"])
            if rph_response["overall_code"] == "OVER_LIMIT":
                overall_code = "OVER_LIMIT"
                return RateLimitResponse(overall_code=overall_code, statuses=all_statuses)

        # Process RPD limits if RPM and RPH passed
        if rpd_descriptors:
            rpd_response = await self._process_rate_limits(
                descriptors=rpd_descriptors,
                now_int=now_int,
                window_size=WINDOW_SIZE_RPD,  # 24 hours
                parent_otel_span=parent_otel_span,
            )
            all_statuses.extend(rpd_response["statuses"])
            if rpd_response["overall_code"] == "OVER_LIMIT":
                overall_code = "OVER_LIMIT"
                # Process RPD limits if RPM and RPH passed

        if rpw_descriptors:
            rpw_response = await self._process_rate_limits(
                descriptors=rpw_descriptors,
                now_int=now_int,
                window_size=WINDOW_SIZE_RPW,
                parent_otel_span=parent_otel_span,
            )
            all_statuses.extend(rpw_response["statuses"])
            if rpw_response["overall_code"] == "OVER_LIMIT":
                overall_code = "OVER_LIMIT"

        if rpmo_descriptors:
            rpmo_response = await self._process_rate_limits(
                descriptors=rpw_descriptors,
                now_int=now_int,
                window_size=WINDOW_SIZE_RPMO,
                parent_otel_span=parent_otel_span,
            )
            all_statuses.extend(rpmo_response["statuses"])
            if rpmo_response["overall_code"] == "OVER_LIMIT":
                overall_code = "OVER_LIMIT"

        return RateLimitResponse(overall_code=overall_code, statuses=all_statuses)


    async def _process_rate_limits(
        self,
        descriptors: List[RateLimitDescriptor],
        now_int: int,
        window_size: int,
        parent_otel_span: Optional[Span] = None,
    ) -> RateLimitResponse:
        """
        Process rate limits for a specific window size.
        """
        keys_to_fetch: List[str] = []
        key_metadata = {}

        for descriptor in descriptors:
            descriptor_key = descriptor["key"]
            descriptor_value = descriptor["value"]
            rate_limit = descriptor.get("rate_limit", {}) or {}
            requests_limit = rate_limit.get("requests_per_unit")
            tokens_limit = rate_limit.get("tokens_per_unit")
            max_parallel_requests_limit = rate_limit.get("max_parallel_requests")
            window_size = rate_limit.get("window_size") or self.window_size

            window_key = f"{{{descriptor_key}:{descriptor_value}}}:window"

            rate_limit_set = False
            if requests_limit is not None:
                rpm_key = self.create_rate_limit_keys(
                    descriptor_key, descriptor_value, "requests"
                )
                keys_to_fetch.extend([window_key, rpm_key])
                rate_limit_set = True
            if tokens_limit is not None:
                tpm_key = self.create_rate_limit_keys(
                    descriptor_key, descriptor_value, "tokens"
                )
                keys_to_fetch.extend([window_key, tpm_key])
                rate_limit_set = True
            if max_parallel_requests_limit is not None:
                max_parallel_requests_key = self.create_rate_limit_keys(
                    descriptor_key, descriptor_value, "max_parallel_requests"
                )
                keys_to_fetch.extend([window_key, max_parallel_requests_key])
                rate_limit_set = True

            if not rate_limit_set:
                continue

            key_metadata[window_key] = {
                "requests_limit": int(requests_limit)
                if requests_limit is not None
                else None,
                "tokens_limit": int(tokens_limit) if tokens_limit is not None else None,
                "max_parallel_requests_limit": int(max_parallel_requests_limit)
                if max_parallel_requests_limit is not None
                else None,
                "window_size": int(window_size),
                "descriptor_key": descriptor_key,
            }

        ## CHECK IN-MEMORY CACHE
        cache_values = await self.internal_usage_cache.async_batch_get_cache(
            keys=keys_to_fetch,
            parent_otel_span=parent_otel_span,
            local_only=True,
        )

        if cache_values is not None:
            rate_limit_response = self.is_cache_list_over_limit(
                keys_to_fetch, cache_values, key_metadata
            )
            if rate_limit_response["overall_code"] == "OVER_LIMIT":
                return rate_limit_response

        ## IF under limit, check Redis
        if self.batch_rate_limiter_script is not None:
            cache_values = await self.batch_rate_limiter_script(
                keys=keys_to_fetch,
                args=[now_int, window_size],  # Use integer timestamp
            )

            # update in-memory cache with new values
            for i in range(0, len(cache_values), 2):
                window_key = keys_to_fetch[i]
                counter_key = keys_to_fetch[i + 1]
                window_value = cache_values[i]
                counter_value = cache_values[i + 1]
                await self.internal_usage_cache.async_set_cache(
                    key=counter_key,
                    value=counter_value,
                    ttl=window_size,
                    litellm_parent_otel_span=parent_otel_span,
                    local_only=True,
                )
                await self.internal_usage_cache.async_set_cache(
                    key=window_key,
                    value=window_value,
                    ttl=window_size,
                    litellm_parent_otel_span=parent_otel_span,
                    local_only=True,
                )
        else:
            cache_values = await self.in_memory_cache_sliding_window(
                keys=keys_to_fetch,
                now_int=now_int,
                window_size=self.window_size,
            )

        rate_limit_response = self.is_cache_list_over_limit(
            keys_to_fetch, cache_values, key_metadata
        )
        return rate_limit_response

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,
    ):
        """
        Pre-call hook to check rate limits before making the API call.
        """
        from litellm.proxy.auth.auth_utils import (
            get_key_model_rpm_limit,
            get_key_model_rph_limit,
            get_key_model_rpd_limit,
            get_key_model_rpw_limit,
            get_key_model_rpmo_limit,
            # get_key_model_tpm_limit,
        )

        verbose_proxy_logger.debug("Inside Rate Limit Pre-Call Hook")

        # Create rate limit descriptors
        descriptors = []

        # API Key rate limits
        # if user_api_key_dict.api_key:
        #     descriptors.append(
        #         RateLimitDescriptor(
        #             key="api_key",
        #             value=user_api_key_dict.api_key,
        #             rate_limit={
        #                 "requests_per_unit": user_api_key_dict.rpm_limit,
        #                 "tokens_per_unit": user_api_key_dict.tpm_limit,
        #                 "max_parallel_requests": user_api_key_dict.max_parallel_requests,
        #                 "window_size": self.window_size,  # 1 minute window
        #             },
        #         )
        #     )

        # User rate limits
        # if user_api_key_dict.user_id:
        #     descriptors.append(
        #         RateLimitDescriptor(
        #             key="user",
        #             value=user_api_key_dict.user_id,
        #             rate_limit={
        #                 "requests_per_unit": user_api_key_dict.user_rpm_limit,
        #                 "tokens_per_unit": user_api_key_dict.user_tpm_limit,
        #                 "window_size": self.window_size,
        #             },
        #         )
        #     )

        # Team rate limits
        # if user_api_key_dict.team_id:
        #     descriptors.append(
        #         RateLimitDescriptor(
        #             key="team",
        #             value=user_api_key_dict.team_id,
        #             rate_limit={
        #                 "requests_per_unit": user_api_key_dict.team_rpm_limit,
        #                 "tokens_per_unit": user_api_key_dict.team_tpm_limit,
        #                 "window_size": self.window_size,
        #             },
        #         )
        #     )

        # End user rate limits
        # if user_api_key_dict.end_user_id:
        #     descriptors.append(
        #         RateLimitDescriptor(
        #             key="end_user",
        #             value=user_api_key_dict.end_user_id,
        #             rate_limit={
        #                 "requests_per_unit": user_api_key_dict.end_user_rpm_limit,
        #                 "tokens_per_unit": user_api_key_dict.end_user_tpm_limit,
        #                 "window_size": self.window_size,
        #             },
        #         )
        #     )

        # Model rate limits
        requested_model = data.get("model", None)
        if requested_model and (
            # get_key_model_tpm_limit(user_api_key_dict) is not None
            get_key_model_rpm_limit(user_api_key_dict) is not None
            or get_key_model_rph_limit(user_api_key_dict) is not None
            or get_key_model_rpd_limit(user_api_key_dict) is not None
            or get_key_model_rpw_limit(user_api_key_dict) is not None
            or get_key_model_rpmo_limit(user_api_key_dict) is not None
        ):
            # _tpm_limit_for_key_model = get_key_model_tpm_limit(user_api_key_dict) or {}
            _rpm_limit_for_key_model = get_key_model_rpm_limit(user_api_key_dict) or {}
            _rph_limit_for_key_model = get_key_model_rph_limit(user_api_key_dict) or {}
            _rpd_limit_for_key_model = get_key_model_rpd_limit(user_api_key_dict) or {}
            _rpw_limit_for_key_model = get_key_model_rpw_limit(user_api_key_dict) or {}
            _rpmo_limit_for_key_model = get_key_model_rpmo_limit(user_api_key_dict) or {}
            should_check_rate_limit = False
            # if requested_model in _tpm_limit_for_key_model:
            #     should_check_rate_limit = True
            if requested_model in _rpm_limit_for_key_model:
                should_check_rate_limit = True
            if requested_model in _rph_limit_for_key_model:
                should_check_rate_limit = True
            if requested_model in _rpd_limit_for_key_model:
                should_check_rate_limit = True
            if requested_model in _rpw_limit_for_key_model:
                should_check_rate_limit = True
            if requested_model in _rpmo_limit_for_key_model:
                should_check_rate_limit = True

            if should_check_rate_limit:
                # model_specific_tpm_limit: Optional[int] = None
                model_specific_rpm_limit: Optional[int] = None
                model_specific_rph_limit: Optional[int] = None
                model_specific_rph_limit: Optional[int] = None
                model_specific_rpd_limit: Optional[int] = None
                model_specific_rpw_limit: Optional[int] = None
                model_specific_rpmo_limit: Optional[int] = None
                # if requested_model in _tpm_limit_for_key_model:
                #     model_specific_tpm_limit = _tpm_limit_for_key_model[requested_model]
                if requested_model in _rpm_limit_for_key_model:
                    model_specific_rpm_limit = _rpm_limit_for_key_model[requested_model]
                if requested_model in _rph_limit_for_key_model:
                    model_specific_rph_limit = _rph_limit_for_key_model[requested_model]
                if requested_model in _rpd_limit_for_key_model:
                    model_specific_rpd_limit = _rpd_limit_for_key_model[requested_model]
                if requested_model in _rpw_limit_for_key_model:
                    model_specific_rpw_limit = _rpw_limit_for_key_model[requested_model]
                if requested_model in _rpmo_limit_for_key_model:
                    model_specific_rpmo_limit = _rpmo_limit_for_key_model[requested_model]
                # if model_specific_rpm_limit is not None or model_specific_tpm_limit is not None:
                if model_specific_rpm_limit is not None:
                    descriptors.append(
                        RateLimitDescriptor(
                            key="model_per_key",
                            value=f"{user_api_key_dict.user_id}:{requested_model}:rpm",
                            rate_limit={
                                "requests_per_unit": model_specific_rpm_limit,
                                # "tokens_per_unit": model_specific_tpm_limit,
                                "window_size": WINDOW_SIZE_RPM,  # 1 minute window
                            },
                        )
                    )
                if model_specific_rph_limit is not None:
                    descriptors.append(
                        RateLimitDescriptor(
                            key="model_per_key",
                            value=f"{user_api_key_dict.user_id}:{requested_model}:rph",
                            rate_limit={
                                "requests_per_unit": model_specific_rph_limit,
                                "window_size": WINDOW_SIZE_RPH,  # 1 hour window
                            },
                        )
                    )
                if model_specific_rpd_limit is not None:
                    descriptors.append(
                        RateLimitDescriptor(
                            key="model_per_key",
                            value=f"{user_api_key_dict.user_id}:{requested_model}:rpd",
                            rate_limit={
                                "requests_per_unit": model_specific_rpd_limit,
                                "window_size": WINDOW_SIZE_RPD,  # 24 hour window
                            },
                        )
                    )
                if model_specific_rpw_limit is not None:
                    descriptors.append(
                        RateLimitDescriptor(
                            key="model_per_key",
                            value=f"{user_api_key_dict.user_id}:{requested_model}:rpw",
                            rate_limit={
                                "requests_per_unit": model_specific_rpw_limit,
                                "window_size": WINDOW_SIZE_RPW,
                            },
                        )
                    )
                if model_specific_rpmo_limit is not None:
                    descriptors.append(
                        RateLimitDescriptor(
                            key="model_per_key",
                            value=f"{user_api_key_dict.user_id}:{requested_model}:rpmo",
                            rate_limit={
                                "requests_per_unit": model_specific_rpmo_limit,
                                "window_size": WINDOW_SIZE_RPW,
                            },
                        )
                    )

        # Check rate limits
        response = await self.should_rate_limit(
            descriptors=descriptors,
            parent_otel_span=user_api_key_dict.parent_otel_span,
        )

        if response["overall_code"] == "OVER_LIMIT":
            # Find which descriptor hit the limit
            for i, status in enumerate(response["statuses"]):
                if status["code"] == "OVER_LIMIT":
                    descriptor = descriptors[i]
                    remaining = int(status["limit_remaining"]) if int(status["limit_remaining"]) >= 0 else 0
                    detail=f"Rate limit exceeded for {descriptor['key']}: {descriptor['value']}. Limit: {status['current_limit']}, Remaining: {remaining}",
                    if litellm.enable_lazy_rate_limit_exception_for_parallel_request_limiter:
                        data.setdefault("metadata", {})
                        data["metadata"]["lazy_rate_limit_exception_for_parallel_request_limiter"] = detail
                        return
                    headers = {}
                    if int(descriptor["rate_limit"]["window_size"]) == WINDOW_SIZE_RPM:
                        headers["retry-after"] = str(WINDOW_SIZE_RPM)
                    raise HTTPException(
                        status_code=429,
                        detail=detail,
                        headers=headers,
                    )

    # def _create_pipeline_operations(
    #     self,
    #     key: str,
    #     value: str,
    #     rate_limit_type: Literal["requests", "tokens", "max_parallel_requests"],
    #     total_tokens: int,
    # ) -> List["RedisPipelineIncrementOperation"]:
    #     """
    #     Create pipeline operations for TPM increments
    #     """
    #     from litellm.types.caching import RedisPipelineIncrementOperation

    #     pipeline_operations: List[RedisPipelineIncrementOperation] = []
    #     counter_key = self.create_rate_limit_keys(
    #         key=key,
    #         value=value,
    #         rate_limit_type="tokens",
    #     )
    #     pipeline_operations.append(
    #         RedisPipelineIncrementOperation(
    #             key=counter_key,
    #             increment_value=total_tokens,
    #             ttl=self.window_size,
    #         )
    #     )

    #     return pipeline_operations

    def get_rate_limit_type(self) -> Literal["output", "input", "total"]:
        from litellm.proxy.proxy_server import general_settings

        specified_rate_limit_type = general_settings.get(
            "token_rate_limit_type", "output"
        )
        if not specified_rate_limit_type or specified_rate_limit_type not in [
            "output",
            "input",
            "total",
        ]:
            return "total"  # default to total
        return specified_rate_limit_type

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Update TPM usage on successful API calls by incrementing counters using pipeline
        """
        from litellm.litellm_core_utils.core_helpers import (
            _get_parent_otel_span_from_kwargs,
        )
        from litellm.proxy.common_utils.callback_utils import (
            get_model_group_from_litellm_kwargs,
        )
        from litellm.types.caching import RedisPipelineIncrementOperation
        from litellm.types.utils import ModelResponse, Usage

        rate_limit_type = self.get_rate_limit_type()

        litellm_parent_otel_span: Union[Span, None] = _get_parent_otel_span_from_kwargs(
            kwargs
        )
        try:
            verbose_proxy_logger.debug(
                "INSIDE parallel request limiter ASYNC SUCCESS LOGGING"
            )

            # Get metadata from kwargs
            user_api_key = kwargs["litellm_params"]["metadata"].get("user_api_key")
            # user_api_key_user_id = kwargs["litellm_params"]["metadata"].get(
            #     "user_api_key_user_id"
            # )
            # user_api_key_team_id = kwargs["litellm_params"]["metadata"].get(
            #     "user_api_key_team_id"
            # )
            # user_api_key_end_user_id = kwargs.get("user") or kwargs["litellm_params"][
            #     "metadata"
            # ].get("user_api_key_end_user_id")
            model_group = get_model_group_from_litellm_kwargs(kwargs)

            # Get total tokens from response
            total_tokens = 0
            if isinstance(response_obj, ModelResponse):
                _usage = getattr(response_obj, "usage", None)
                if _usage and isinstance(_usage, Usage):
                    if rate_limit_type == "output":
                        total_tokens = _usage.completion_tokens
                    elif rate_limit_type == "input":
                        total_tokens = _usage.prompt_tokens
                    elif rate_limit_type == "total":
                        total_tokens = _usage.total_tokens

            # Create pipeline operations for TPM increments
            pipeline_operations: List[RedisPipelineIncrementOperation] = []

            # API Key TPM
            # if user_api_key:
            #     # MAX PARALLEL REQUESTS - only support for API Key, just decrement the counter
            #     counter_key = self.create_rate_limit_keys(
            #         key="api_key",
            #         value=user_api_key,
            #         rate_limit_type="max_parallel_requests",
            #     )
            #     pipeline_operations.append(
            #         RedisPipelineIncrementOperation(
            #             key=counter_key,
            #             increment_value=-1,
            #             ttl=self.window_size,
            #         )
            #     )
            #     pipeline_operations.extend(
            #         self._create_pipeline_operations(
            #             key="api_key",
            #             value=user_api_key,
            #             rate_limit_type="tokens",
            #             total_tokens=total_tokens,
            #         )
            #     )

            # User TPM
            # if user_api_key_user_id:
            #     # TPM
            #     pipeline_operations.extend(
            #         self._create_pipeline_operations(
            #             key="user",
            #             value=user_api_key_user_id,
            #             rate_limit_type="tokens",
            #             total_tokens=total_tokens,
            #         )
            #     )

            # Team TPM
            # if user_api_key_team_id:
            #     pipeline_operations.extend(
            #         self._create_pipeline_operations(
            #             key="team",
            #             value=user_api_key_team_id,
            #             rate_limit_type="tokens",
            #             total_tokens=total_tokens,
            #         )
            #     )

            # End User TPM
            # if user_api_key_end_user_id:
            #     pipeline_operations.extend(
            #         self._create_pipeline_operations(
            #             key="end_user",
            #             value=user_api_key_end_user_id,
            #             rate_limit_type="tokens",
            #             total_tokens=total_tokens,
            #         )
            #     )

            # Model-specific TPM
            # if model_group and user_api_key:
            #     pipeline_operations.extend(
            #         self._create_pipeline_operations(
            #             key="model_per_key",
            #             value=f"{user_api_key}:{model_group}",
            #             rate_limit_type="tokens",
            #             total_tokens=total_tokens,
            #         )
            #     )

            # Execute all increments in a single pipeline
            if pipeline_operations:
                await self.internal_usage_cache.dual_cache.async_increment_cache_pipeline(
                    increment_list=pipeline_operations,
                    litellm_parent_otel_span=litellm_parent_otel_span,
                )

        except Exception as e:
            verbose_proxy_logger.exception(
                f"Error in rate limit success event: {str(e)}"
            )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """
        Decrement max parallel requests counter for the API Key
        """
        from litellm.litellm_core_utils.core_helpers import (
            _get_parent_otel_span_from_kwargs,
        )
        from litellm.types.caching import RedisPipelineIncrementOperation

        try:
            litellm_parent_otel_span: Union[
                Span, None
            ] = _get_parent_otel_span_from_kwargs(kwargs)
            user_api_key = kwargs["litellm_params"]["metadata"].get("user_api_key")
            pipeline_operations: List[RedisPipelineIncrementOperation] = []

            if user_api_key:
                # MAX PARALLEL REQUESTS - only support for API Key, just decrement the counter
                counter_key = self.create_rate_limit_keys(
                    key="api_key",
                    value=user_api_key,
                    rate_limit_type="max_parallel_requests",
                )
                pipeline_operations.append(
                    RedisPipelineIncrementOperation(
                        key=counter_key,
                        increment_value=-1,
                        ttl=self.window_size,
                    )
                )

            # Execute all increments in a single pipeline
            if pipeline_operations:
                await self.internal_usage_cache.dual_cache.async_increment_cache_pipeline(
                    increment_list=pipeline_operations,
                    litellm_parent_otel_span=litellm_parent_otel_span,
                )
        except Exception as e:
            verbose_proxy_logger.exception(
                f"Error in rate limit failure event: {str(e)}"
            )

    async def async_post_call_success_hook(
        self, data: dict, user_api_key_dict: UserAPIKeyAuth, response
    ):
        """
        Post-call hook to update rate limit headers in the response.
        """
        pass
        # try:
        #     descriptors = []

        #     # API Key
        #     if user_api_key_dict.api_key:
        #         descriptors.append(
        #             RateLimitDescriptor(
        #                 key="api_key",
        #                 value=user_api_key_dict.api_key,
        #                 rate_limit={
        #                     "requests_per_unit": user_api_key_dict.rpm_limit
        #                     or sys.maxsize,
        #                     "window_size": self.window_size,
        #                 },
        #             )
        #         )

        #     # Check rate limits
        #     # rate_limit_response = await self.should_rate_limit(
        #     #     descriptors=descriptors,
        #     #     parent_otel_span=user_api_key_dict.parent_otel_span,
        #     #     read_only=True,
        #     # )

        #     # # Update response headers
        #     # if hasattr(response, "_hidden_params"):
        #     #     _hidden_params = getattr(response, "_hidden_params")
        #     # else:
        #     #     _hidden_params = None

        #     # if _hidden_params is not None and (
        #     #     isinstance(_hidden_params, BaseModel)
        #     #     or isinstance(_hidden_params, dict)
        #     # ):
        #     #     if isinstance(_hidden_params, BaseModel):
        #     #         _hidden_params = _hidden_params.model_dump()

        #     #     _additional_headers = _hidden_params.get("additional_headers", {}) or {}

        #     #     # Add rate limit headers
        #     #     for i, status in enumerate(rate_limit_response["statuses"]):
        #     #         descriptor = descriptors[i]
        #     #         prefix = f"x-ratelimit-{descriptor['key']}"
        #     #         _additional_headers[f"{prefix}-remaining-requests"] = status[
        #     #             "limit_remaining"
        #     #         ]
        #     #         _additional_headers[f"{prefix}-limit-requests"] = status[
        #     #             "current_limit"
        #     #         ]

        #     #     setattr(
        #     #         response,
        #     #         "_hidden_params",
        #     #         {**_hidden_params, "additional_headers": _additional_headers},
        #     #     )

        # except Exception as e:
        #     verbose_proxy_logger.exception(
        #         f"Error in rate limit post-call hook: {str(e)}"
        #     )
