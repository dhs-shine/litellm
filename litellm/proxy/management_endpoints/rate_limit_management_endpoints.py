from datetime import datetime
from datetime import timezone
from typing import Any, Dict, Optional
from litellm.proxy.auth.auth_utils import (
    get_key_model_rpm_limit,
    get_key_model_rph_limit,
    get_key_model_rpd_limit,
    get_key_model_rpw_limit,
    get_key_model_rpmo_limit,
)

# Rate limit window sizes in seconds
WINDOW_SIZE_RPM = 60  # 1 minute
WINDOW_SIZE_RPH = 3600  # 1 hour
WINDOW_SIZE_RPD = 86400  # 1 day
WINDOW_SIZE_RPW = 604800  # 1 week
WINDOW_SIZE_RPMO = 2592000  # 1 month (30 days)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.utils import (
    handle_exception_on_proxy,
)

router = APIRouter()

def _get_current_limit_for_type(rate_limit_type: str, user_api_key_dict: UserAPIKeyAuth, model: str) -> int:
    """
    Retrieves the current rate limit based on the rate limit type for a specific model.
    """
    limit_dict = None
    if rate_limit_type == "rpm":
        limit_dict = get_key_model_rpm_limit(user_api_key_dict)
    elif rate_limit_type == "rph":
        limit_dict = get_key_model_rph_limit(user_api_key_dict)
    elif rate_limit_type == "rpd":
        limit_dict = get_key_model_rpd_limit(user_api_key_dict)
    elif rate_limit_type == "rpw":
        limit_dict = get_key_model_rpw_limit(user_api_key_dict)
    elif rate_limit_type == "rpmo":
        limit_dict = get_key_model_rpmo_limit(user_api_key_dict)

    if limit_dict is not None and model in limit_dict:
        return limit_dict[model]
    return 0

def get_expiration_timestamp(window_timestamp: float, rate_limit_type: str) -> Optional[float]:
    """
    Calculates the expiration timestamp based on the rate limit type.
    """
    if rate_limit_type == "rpm":
        return window_timestamp + WINDOW_SIZE_RPM
    elif rate_limit_type == "rph":
        return window_timestamp + WINDOW_SIZE_RPH
    elif rate_limit_type == "rpd":
        return window_timestamp + WINDOW_SIZE_RPD
    elif rate_limit_type == "rpw":
        return window_timestamp + WINDOW_SIZE_RPW
    elif rate_limit_type == "rpmo":
        return window_timestamp + WINDOW_SIZE_RPMO
    else:
        return None

@router.get(
    "/v1/ratelimit/info",
    tags=["rate limit management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=Dict[str, Any],
)
async def get_model_per_key_rate_limit_info(
    model: str = Query("gemini-2.5-flash", description="The model to get rate limit info for"),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Retrieve model-per-key rate limit information (limit_remaining and current_limit).

    Parameters:
        api_key: (str) The API key to get rate limit info for.
        model: (str) The model to get rate limit info for.
        user_api_key_dict: UserAPIKeyAuth = Dependency representing the user's API key.
    Returns:
        Dict containing the rate limit information for the specified API key and model.
    """
    try:
        if user_api_key_dict.api_key is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "API key not found in request."},
            )

        from litellm.proxy.proxy_server import proxy_logging_obj
        if proxy_logging_obj is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Internal usage cache not initialized."},
            )

        rate_limit_data: Dict[str, Any] = {"model": model}
        # Construct cache key
        rate_limit_types = ["rpm", "rph", "rpd", "rpw", "rpmo"]
        for rate_limit_type in rate_limit_types:
            key_prefix = f"{{model_per_key:{user_api_key_dict.user_id}:{model}:{rate_limit_type}}}"
            counter_key = f"{key_prefix}:requests"
            window_key = f"{key_prefix}:window"

            # Fetch rate limit data from cache
            counter_value = await proxy_logging_obj.internal_usage_cache.async_get_cache(key=counter_key, litellm_parent_otel_span=None)
            if counter_value:
                window_value = await proxy_logging_obj.internal_usage_cache.async_get_cache(key=window_key, litellm_parent_otel_span=None)
                refreshed_at = datetime.fromtimestamp(window_value, tz=timezone.utc).isoformat() if window_value else None
                current_limit = _get_current_limit_for_type(rate_limit_type, user_api_key_dict, model)
                limit_remaining = max(0, current_limit - counter_value)

                # Calculate expiration time
                expired_at = None
                if window_value:
                    expiration_timestamp = get_expiration_timestamp(window_value, rate_limit_type)
                    expired_at = datetime.fromtimestamp(expiration_timestamp, tz=timezone.utc).isoformat() if expiration_timestamp else None

                rate_limit_data[rate_limit_type] = {
                    "refreshed_at": refreshed_at,
                    "current_limit": current_limit,
                    "limit_remaining": limit_remaining,
                    "expired_at": expired_at,
                }

        return rate_limit_data

    except Exception as e:
        verbose_proxy_logger.error(f"Error getting model per key rate limit info: {e}")
        raise handle_exception_on_proxy(e)
