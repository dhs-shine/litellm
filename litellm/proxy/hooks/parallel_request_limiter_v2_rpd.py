"""
V2 Implementation of Parallel Requests, TPM, RPM Limiting on the proxy

Designed to work on a multi-instance setup, where multiple instances are writing to redis simultaneously
"""
import asyncio
import sys
from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

from fastapi import HTTPException

import litellm
from litellm import DualCache, ModelResponse
from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.core_helpers import _get_parent_otel_span_from_kwargs
from litellm.proxy._types import CommonProxyErrors, UserAPIKeyAuth
from litellm.proxy.auth.auth_utils import (
    get_key_model_rpm_limit,
    get_key_model_tpm_limit,
    get_key_model_rpd_limit,
)
from litellm.router_strategy.base_routing_strategy import BaseRoutingStrategy

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    from litellm.proxy.utils import InternalUsageCache as _InternalUsageCache

    Span = Union[_Span, Any]
    InternalUsageCache = _InternalUsageCache
else:
    Span = Any
    InternalUsageCache = Any

RateLimitGroupsPerMinute = Literal["request_count", "tpm", "rpm"]
RateLimitGroupsPerHour = Literal["rph"]
RateLimitGroupsPerDay = Literal["rpd"]
RateLimitTypes = Literal["key", "model_per_key", "user", "customer", "team"]


class _PROXY_MaxParallelRequestsHandler_v2_RateLimitPerDay(BaseRoutingStrategy, CustomLogger):
    # Class variables or attributes
    def __init__(self, internal_usage_cache: InternalUsageCache):
        self.internal_usage_cache = internal_usage_cache
        BaseRoutingStrategy.__init__(
            self,
            dual_cache=internal_usage_cache.dual_cache,
            should_batch_redis_writes=True,
            default_sync_interval=1,
        )
        self.minute_ttl = 60
        self.day_ttl = 86400

    def print_verbose(self, print_statement):
        try:
            verbose_proxy_logger.debug(print_statement)
            if litellm.set_verbose:
                print(print_statement)  # noqa
        except Exception:
            pass

    @property
    def prefix(self) -> str:
        return "parallel_request_limiter_v2"

    def _get_current_usage_key_per_minute(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        precise_minute: str,
        model: Optional[str],
        rate_limit_type: Literal["key", "model_per_key", "user", "customer", "team"],
        group: RateLimitGroupsPerMinute,
    ) -> Optional[str]:
        # if rate_limit_type == "key" and user_api_key_dict.api_key is not None:
        #     return (
        #         f"{self.prefix}::{user_api_key_dict.api_key}::{precise_minute}::{group}"
        #     )
        # elif (
        #     rate_limit_type == "model_per_key"
        #     and model is not None
        #     and user_api_key_dict.api_key is not None
        # ):
        #     return f"{self.prefix}::{user_api_key_dict.api_key}::{model}::{precise_minute}::{group}"
        # elif rate_limit_type == "user" and user_api_key_dict.user_id is not None:
        #     return (
        #         f"{self.prefix}::{user_api_key_dict.user_id}::{precise_minute}::{group}"
        #     )
        # elif (
        #     rate_limit_type == "customer" and user_api_key_dict.end_user_id is not None
        # ):
        #     return f"{self.prefix}::{user_api_key_dict.end_user_id}::{precise_minute}::{group}"
        # elif rate_limit_type == "team" and user_api_key_dict.team_id is not None:
        #     return (
        #         f"{self.prefix}::{user_api_key_dict.team_id}::{precise_minute}::{group}"
        #     )
        if rate_limit_type == "model_per_key" and model is not None:
            return f"{self.prefix}::{user_api_key_dict.api_key}::{model}::{precise_minute}::{group}"
        else:
            return None

    def _get_current_usage_key_per_day(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        precise_date: str,
        model: Optional[str],
        rate_limit_type: Literal["key", "model_per_key", "user", "customer", "team"],
        group: RateLimitGroupsPerDay,
    ) -> Optional[str]:
        if rate_limit_type == "model_per_key":
            return f"{self.prefix}::{user_api_key_dict.api_key}::{model}::{precise_date}::{group}"
        else:
            return None

    def get_key_pattern_to_sync(self) -> Optional[str]:
        return self.prefix + "::"

    def _get_slots_to_check_per_minute(self, current_slot: int) -> List[str]:
        slots_to_check = []
        current_time = datetime.now()
        for i in range(4):
            slot_number = (current_slot - i) % 4  # This ensures we wrap around properly
            minute = current_time.minute
            hour = current_time.hour

            # If we need to look at previous minute
            if current_slot - i < 0:
                if minute == 0:
                    # If we're at minute 0, go to previous hour
                    hour = (current_time.hour - 1) % 24
                    minute = 59
                else:
                    minute = current_time.minute - 1

            slot_key = f"{current_time.strftime('%Y-%m-%d')}-{hour:02d}-{minute:02d}-{slot_number}"
            slots_to_check.append(slot_key)
        return slots_to_check

    async def check_key_in_limits_v2_per_minute(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        data: dict,
        max_parallel_requests: Optional[int],
        precise_minute: str,
        tpm_limit: Optional[int],
        rpm_limit: Optional[int],
        rate_limit_type: Literal["key", "model_per_key", "user", "customer", "team"],
    ):
        ## INCREMENT CURRENT USAGE
        increment_list: List[Tuple[str, int]] = []
        decrement_list: List[Tuple[str, int]] = []
        slots_to_check: List[str] = []
        increment_value_by_group = {
            "request_count": 1,
            "tpm": 0,
            "rpm": 1,
        }

        # Get current time and calculate the last 4 15s slots
        current_time = datetime.now()
        current_slot = (
            current_time.second // 15
        )  # This gives us 0-3 for the current 15s slot
        slots_to_check = self._get_slots_to_check_per_minute(current_slot)
        slot_cache_keys = []
        # Calculate the last 4 slots, handling minute boundaries

        # For each slot, create keys for request_count, rpm, tpm
        for slot_key in slots_to_check:
            for group in ["request_count", "rpm", "tpm"]:
                key = self._get_current_usage_key_per_minute(
                    user_api_key_dict=user_api_key_dict,
                    precise_minute=slot_key,
                    model=data.get("model", None),
                    rate_limit_type=rate_limit_type,
                    group=cast(RateLimitGroupsPerMinute, group),
                )
                if key is None:
                    continue
                # Only increment the current slot
                if slot_key == slots_to_check[0]:
                    increment_list.append((key, increment_value_by_group[group]))
                    decrement_list.append(
                        (key, -1 if increment_value_by_group[group] == 1 else 0)
                    )
                else:
                    self.add_to_in_memory_keys_to_update(key=key)
                slot_cache_keys.append(key)

        if (
            not max_parallel_requests and not rpm_limit and not tpm_limit
        ):  # no rate limits
            return

        await self._increment_value_list_in_current_window(
            increment_list=increment_list,
            ttl=self.minute_ttl,
        )

        # Get the current values for all slots to check limits
        current_values = await self.internal_usage_cache.async_batch_get_cache(
            slot_cache_keys
        )
        if current_values is None:
            current_values = [None] * len(slot_cache_keys)

        # Calculate totals across all slots, handling None values
        # Group values by type (request_count, rpm, tpm, rpd)
        total_requests = 0
        total_rpm = 0
        total_tpm = 0

        # Map keys to their corresponding values
        key_to_value_map = {slot_cache_keys[i]: current_values[i] for i in range(len(slot_cache_keys))}

        # Sum up values for each group
        for slot_key in slots_to_check:
            for group in ["request_count", "rpm", "tpm"]:
                key = self._get_current_usage_key_per_minute(
                    user_api_key_dict=user_api_key_dict,
                    precise_minute=slot_key,
                    model=data.get("model", None),
                    rate_limit_type=rate_limit_type,
                    group=cast(RateLimitGroupsPerMinute, group),
                )
                if key in key_to_value_map:
                    value = key_to_value_map[key]
                    if value is not None:
                        if group == "request_count":
                            total_requests += int(value)
                        elif group == "rpm":
                            total_rpm += int(value)
                        elif group == "tpm":
                            total_tpm += int(value)

        should_raise_error = False
        if max_parallel_requests is not None:
            should_raise_error = total_requests > max_parallel_requests
        if rpm_limit is not None:
            should_raise_error = should_raise_error or total_rpm > rpm_limit
        if tpm_limit is not None:
            should_raise_error = should_raise_error or total_tpm > tpm_limit

        if should_raise_error:
            ## DECREMENT CURRENT USAGE - so we don't keep failing subsequent requests
            await self._increment_value_list_in_current_window(
                increment_list=decrement_list,
                ttl=self.minute_ttl,
            )

            additional_details=f"{CommonProxyErrors.max_parallel_request_limit_reached.value}. Hit limit for {rate_limit_type}. Current usage: max_parallel_requests: {total_requests}, current_rpm: {total_rpm}, current_tpm: {total_tpm}. Current limits: max_parallel_requests: {max_parallel_requests}, rpm_limit: {rpm_limit}, tpm_limit: {tpm_limit}."
            if litellm.enable_lazy_rate_limit_exception_for_parallel_request_limiter:
                data.setdefault("metadata", {})
                data["metadata"]["lazy_rate_limit_exception_for_parallel_request_limiter"] = additional_details
                return

            raise self.raise_rate_limit_error(
                additional_details=additional_details
            )

    async def check_key_in_limits_v2_per_day(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        data: dict,
        precise_date: str,
        rpd_limit: Optional[int],
        rate_limit_type: Literal["key", "model_per_key", "user", "customer", "team"],
    ):
        ## INCREMENT CURRENT USAGE
        increment_list: List[Tuple[str, int]] = []
        decrement_list: List[Tuple[str, int]] = []
        increment_value_by_group = {
            "rpd": 1,
        }

        slot_cache_keys = []
        # Calculate the last 4 slots, handling minute boundaries

        # Add RPD key separately, using current_date instead of precise_minute
        rpd_key = self._get_current_usage_key_per_day(
            user_api_key_dict=user_api_key_dict,
            precise_date=precise_date,
            model=data.get("model", None),
            rate_limit_type=rate_limit_type,
            group=cast(RateLimitGroupsPerDay, "rpd"),
        )
        if rpd_key is not None:
            increment_list.append((rpd_key, increment_value_by_group["rpd"]))
            decrement_list.append((rpd_key, -1 if increment_value_by_group["rpd"] == 1 else 0))
            slot_cache_keys.append(rpd_key)

        if (
            not rpd_limit
        ):  # no rate limits
            return

        await self._increment_value_list_in_current_window(
            increment_list=increment_list,
            ttl=self.day_ttl,
        )

        # Get the current values for all slots to check limits
        current_values = await self.internal_usage_cache.async_batch_get_cache(
            slot_cache_keys
        )
        if current_values is None:
            current_values = [None] * len(slot_cache_keys)

        # Calculate totals across all slots, handling None values
        # Group values by type (request_count, rpm, tpm, rpd)
        total_rpd = 0

        # Map keys to their corresponding values
        key_to_value_map = {slot_cache_keys[i]: current_values[i] for i in range(len(slot_cache_keys))}

        # Get RPD value separately
        rpd_key = self._get_current_usage_key_per_day(
            user_api_key_dict=user_api_key_dict,
            precise_date=precise_date,
            model=data.get("model", None),
            rate_limit_type=rate_limit_type,
            group="rpd",
        )
        if rpd_key in key_to_value_map:
            value = key_to_value_map[rpd_key]
            if value is not None:
                total_rpd += int(value)

        should_raise_error = False
        if rpd_limit is not None:
            should_raise_error = should_raise_error or total_rpd > rpd_limit

        if should_raise_error:
            ## DECREMENT CURRENT USAGE - so we don't keep failing subsequent requests
            await self._increment_value_list_in_current_window(
                increment_list=decrement_list,
                ttl=self.day_ttl,
            )

            additional_details=f"{CommonProxyErrors.max_parallel_request_limit_reached.value}. Hit limit for {rate_limit_type}. Current usage: current_rpd: {total_rpd}. Current limits: rpd_limit: {rpd_limit}."
            if litellm.enable_lazy_rate_limit_exception_for_parallel_request_limiter:
                data.setdefault("metadata", {})
                data["metadata"]["lazy_rate_limit_exception_for_parallel_request_limiter"] = additional_details
                return

            raise self.raise_rate_limit_error(
                additional_details=additional_details
            )

    def time_to_next_minute(self) -> float:
        # Get the current time
        now = datetime.now()

        # Calculate the next minute
        next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)

        # Calculate the difference in seconds
        seconds_to_next_minute = (next_minute - now).total_seconds()

        return seconds_to_next_minute

    def raise_rate_limit_error(
        self, additional_details: Optional[str] = None
    ) -> HTTPException:
        """
        Raise an HTTPException with a 429 status code and a retry-after header
        """
        error_message = "Max parallel request limit reached"
        if additional_details is not None:
            error_message = error_message + " " + additional_details
        raise HTTPException(
            status_code=429,
            detail=f"Max parallel request limit reached {additional_details}",
            headers={"retry-after": str(self.time_to_next_minute())},
        )

    async def async_pre_call_hook(  # noqa: PLR0915
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,
    ):
        self.print_verbose("Inside Max Parallel Request Pre-Call Hook")
        api_key = user_api_key_dict.api_key
        max_parallel_requests = user_api_key_dict.max_parallel_requests
        if max_parallel_requests is None:
            max_parallel_requests = sys.maxsize
        if data is None:
            data = {}
        global_max_parallel_requests = data.get("metadata", {}).get(
            "global_max_parallel_requests", None
        )
        tpm_limit = getattr(user_api_key_dict, "tpm_limit", sys.maxsize)
        if tpm_limit is None:
            tpm_limit = sys.maxsize
        rpm_limit = getattr(user_api_key_dict, "rpm_limit", sys.maxsize)
        if rpm_limit is None:
            rpm_limit = sys.maxsize

        # ------------
        # Setup values
        # ------------
        if global_max_parallel_requests is not None:
            # get value from cache
            _key = "global_max_parallel_requests"
            current_global_requests = await self.internal_usage_cache.async_get_cache(
                key=_key,
                local_only=True,
                litellm_parent_otel_span=user_api_key_dict.parent_otel_span,
            )
            # check if below limit
            if current_global_requests is None:
                current_global_requests = 1
            # if above -> raise error
            if current_global_requests >= global_max_parallel_requests:
                return self.raise_rate_limit_error(
                    additional_details=f"Hit Global Limit: Limit={global_max_parallel_requests}, current: {current_global_requests}"
                )
            # if below -> increment
            else:
                await self.internal_usage_cache.async_increment_cache(
                    key=_key,
                    value=1,
                    local_only=True,
                    litellm_parent_otel_span=user_api_key_dict.parent_otel_span,
                )
        requested_model = data.get("model", None)

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_hour = datetime.now().strftime("%H")
        current_minute = datetime.now().strftime("%M")
        precise_minute = f"{current_date}-{current_hour}-{current_minute}"

        tasks = []
        # Disable key, user, team, end_user checks for now
        # if api_key is not None:
        #     # CHECK IF REQUEST ALLOWED for key
        #     tasks.append(
        #         self.check_key_in_limits_v2(
        #             user_api_key_dict=user_api_key_dict,
        #             data=data,
        #             max_parallel_requests=max_parallel_requests,
        #             precise_minute=precise_minute,
        #             tpm_limit=tpm_limit,
        #             rpm_limit=rpm_limit,
        #             rpd_limit=None,
        #             rate_limit_type="key",
        #         )
        #     )
        # if user_api_key_dict.user_id is not None:
        #     # CHECK IF REQUEST ALLOWED for key
        #     tasks.append(
        #         self.check_key_in_limits_v2(
        #             user_api_key_dict=user_api_key_dict,
        #             data=data,
        #             max_parallel_requests=None,
        #             precise_minute=precise_minute,
        #             tpm_limit=user_api_key_dict.user_tpm_limit,
        #             rpm_limit=user_api_key_dict.user_rpm_limit,
        #             rpd_limit=None,
        #             rate_limit_type="user",
        #         )
        #     )
        # if user_api_key_dict.team_id is not None:
        #     tasks.append(
        #         self.check_key_in_limits_v2(
        #             user_api_key_dict=user_api_key_dict,
        #             data=data,
        #             max_parallel_requests=None,
        #             precise_minute=precise_minute,
        #             tpm_limit=user_api_key_dict.team_tpm_limit,
        #             rpm_limit=user_api_key_dict.team_rpm_limit,
        #             rpd_limit=None,
        #             rate_limit_type="team",
        #         )
        #     )
        # if user_api_key_dict.end_user_id is not None:
        #     tasks.append(
        #         self.check_key_in_limits_v2(
        #             user_api_key_dict=user_api_key_dict,
        #             data=data,
        #             max_parallel_requests=None,
        #             precise_minute=precise_minute,
        #             tpm_limit=user_api_key_dict.end_user_tpm_limit,
        #             rpm_limit=user_api_key_dict.end_user_rpm_limit,
        #             rpd_limit=None,
        #             rate_limit_type="customer",
        #         )
        #     )
        if requested_model and (
            get_key_model_tpm_limit(user_api_key_dict) is not None
            or get_key_model_rpm_limit(user_api_key_dict) is not None
            or get_key_model_rpd_limit(user_api_key_dict) is not None
        ):
            _tpm_limit_for_key_model = get_key_model_tpm_limit(user_api_key_dict) or {}
            _rpm_limit_for_key_model = get_key_model_rpm_limit(user_api_key_dict) or {}
            _rpd_limit_for_key_model = get_key_model_rpd_limit(user_api_key_dict) or {}

            should_check_rate_limit = False
            if requested_model in _tpm_limit_for_key_model:
                should_check_rate_limit = True
            elif requested_model in _rpm_limit_for_key_model:
                should_check_rate_limit = True
            elif requested_model in _rpd_limit_for_key_model:
                should_check_rate_limit = True

            if should_check_rate_limit:
                model_specific_tpm_limit: Optional[int] = None
                model_specific_rpm_limit: Optional[int] = None
                if requested_model in _tpm_limit_for_key_model:
                    model_specific_tpm_limit = _tpm_limit_for_key_model[requested_model]
                if requested_model in _rpm_limit_for_key_model:
                    model_specific_rpm_limit = _rpm_limit_for_key_model[requested_model]
                tasks.append(
                    self.check_key_in_limits_v2_per_minute(
                        user_api_key_dict=user_api_key_dict,
                        data=data,
                        max_parallel_requests=None,
                        precise_minute=precise_minute,
                        tpm_limit=model_specific_tpm_limit,
                        rpm_limit=model_specific_rpm_limit,
                        rate_limit_type="model_per_key",
                    )
                )

                model_specific_rpd_limit: Optional[int] = None
                if requested_model in _rpd_limit_for_key_model:
                    model_specific_rpd_limit = _rpd_limit_for_key_model[requested_model]

                tasks.append(
                    self.check_key_in_limits_v2_per_day(
                        user_api_key_dict=user_api_key_dict,
                        data=data,
                        precise_date=current_date,
                        rpd_limit=model_specific_rpd_limit,
                        rate_limit_type="model_per_key",
                    )
                )
        await asyncio.gather(*tasks)

        return

    async def _update_usage_in_cache_post_call_per_minute(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        precise_minute: str,
        model: Optional[str],
        total_tokens: int,
        litellm_parent_otel_span: Union[Span, None] = None,
    ):
        increment_list: List[Tuple[str, int]] = []
        increment_value_by_group = {
            "request_count": -1,
            "tpm": total_tokens,
            "rpm": 0,
        }

        # rate_limit_types = ["key", "user", "customer", "team", "model_per_key"]
        rate_limit_types = ["model_per_key"]
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_slot = (
            current_time.second // 15
        )  # This gives us 0-3 for the current 15s slot
        slot_key = f"{current_time.strftime('%Y-%m-%d')}-{current_hour:02d}-{current_minute:02d}-{current_slot}"
        current_date = f"{current_time.strftime('%Y-%m-%d')}"
        for rate_limit_type in rate_limit_types:
            for group in ["request_count", "rpm", "tpm"]:
                key = self._get_current_usage_key_per_minute(
                    user_api_key_dict=user_api_key_dict,
                    precise_minute=slot_key,
                    model=model,
                    rate_limit_type=cast(RateLimitTypes, rate_limit_type),
                    group=cast(RateLimitGroupsPerMinute, group),
                )
                if key is None:
                    continue
                increment_list.append((key, increment_value_by_group[group]))

            await self._increment_value_list_in_current_window(
                increment_list=increment_list,
                ttl=self.minute_ttl,
            )

    async def _update_usage_in_cache_post_call_per_day(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        precise_date: str,
        model: Optional[str],
        total_tokens: int,
        litellm_parent_otel_span: Union[Span, None] = None,
    ):
        increment_list: List[Tuple[str, int]] = []
        increment_value_by_group = {
            "rpd": 0,
        }

        # rate_limit_types = ["key", "user", "customer", "team", "model_per_key"]
        rate_limit_types = ["model_per_key"]
        for rate_limit_type in rate_limit_types:
            for group in ["rpd"]:
                key = self._get_current_usage_key_per_day(
                    user_api_key_dict=user_api_key_dict,
                    precise_date=precise_date,
                    model=model,
                    rate_limit_type=cast(RateLimitTypes, rate_limit_type),
                    group=cast(RateLimitGroupsPerDay, group),
                )
                if key is None:
                    continue
                increment_list.append((key, increment_value_by_group[group]))

            await self._increment_value_list_in_current_window(
                increment_list=increment_list,
                ttl=self.day_ttl,
            )

    async def async_log_success_event(  # noqa: PLR0915
        self, kwargs, response_obj, start_time, end_time
    ):
        from litellm.proxy.common_utils.callback_utils import (
            get_model_group_from_litellm_kwargs,
        )

        litellm_parent_otel_span: Union[Span, None] = _get_parent_otel_span_from_kwargs(
            kwargs=kwargs
        )
        try:
            self.print_verbose("INSIDE parallel request limiter ASYNC SUCCESS LOGGING")

            # ------------
            # Setup values
            # ------------

            global_max_parallel_requests = kwargs["litellm_params"]["metadata"].get(
                "global_max_parallel_requests", None
            )
            user_api_key = kwargs["litellm_params"]["metadata"]["user_api_key"]
            user_api_key_user_id = kwargs["litellm_params"]["metadata"].get(
                "user_api_key_user_id", None
            )
            user_api_key_team_id = kwargs["litellm_params"]["metadata"].get(
                "user_api_key_team_id", None
            )
            user_api_key_end_user_id = kwargs.get("user") or kwargs["litellm_params"][
                "metadata"
            ].get("user_api_key_end_user_id", None)

            # ------------
            # Setup values
            # ------------

            if global_max_parallel_requests is not None:
                # get value from cache
                _key = "global_max_parallel_requests"
                # decrement
                await self.internal_usage_cache.async_increment_cache(
                    key=_key,
                    value=-1,
                    local_only=True,
                    litellm_parent_otel_span=litellm_parent_otel_span,
                )

            current_date = datetime.now().strftime("%Y-%m-%d")
            current_hour = datetime.now().strftime("%H")
            current_minute = datetime.now().strftime("%M")
            precise_minute = f"{current_date}-{current_hour}-{current_minute}"
            model_group = get_model_group_from_litellm_kwargs(kwargs)
            total_tokens = 0

            if isinstance(response_obj, ModelResponse):
                total_tokens = response_obj.usage.total_tokens  # type: ignore

            # ------------
            # Update usage - API Key
            # ------------

            await self._update_usage_in_cache_post_call_per_minute(
                user_api_key_dict=UserAPIKeyAuth(
                    api_key=user_api_key,
                    user_id=user_api_key_user_id,
                    team_id=user_api_key_team_id,
                    end_user_id=user_api_key_end_user_id,
                ),
                precise_minute=precise_minute,
                model=model_group,
                total_tokens=total_tokens,
            )
            await self._update_usage_in_cache_post_call_per_day(
                user_api_key_dict=UserAPIKeyAuth(
                    api_key=user_api_key,
                    user_id=user_api_key_user_id,
                    team_id=user_api_key_team_id,
                    end_user_id=user_api_key_end_user_id,
                ),
                precise_date=current_date,
                model=model_group,
                total_tokens=total_tokens,
            )

        except Exception as e:
            verbose_proxy_logger.exception(
                "Inside Parallel Request Limiter: An exception occurred - {}".format(
                    str(e)
                )
            )

    async def async_post_call_failure_hook(
        self,
        request_data: dict,
        original_exception: Exception,
        user_api_key_dict: UserAPIKeyAuth,
        traceback_str: Optional[str] = None,
    ):
        try:
            self.print_verbose("Inside Max Parallel Request Failure Hook")

            model_group = request_data.get("model", None)
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_hour = datetime.now().strftime("%H")
            current_minute = datetime.now().strftime("%M")
            precise_minute = f"{current_date}-{current_hour}-{current_minute}"

            ## decrement call count if call failed
            await self._update_usage_in_cache_post_call_per_minute(
                user_api_key_dict=user_api_key_dict,
                precise_minute=precise_minute,
                model=model_group,
                total_tokens=0,
            )
            await self._update_usage_in_cache_post_call_per_day(
                user_api_key_dict=user_api_key_dict,
                precise_date=current_date,
                model=model_group,
                total_tokens=0,
            )
        except Exception as e:
            verbose_proxy_logger.exception(
                "Inside Parallel Request Limiter: An exception occurred - {}".format(
                    str(e)
                )
            )
