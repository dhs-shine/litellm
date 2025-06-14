from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *

from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.utils import (
    handle_exception_on_proxy,
)
import litellm

router = APIRouter()

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
        
        # Construct cache keys
        counter_key = f"{{model_per_key:{user_api_key_dict.api_key}:{model}:rpd}}:requests"

        # # Fetch rate limit data from cache
        counter_value = await proxy_logging_obj.internal_usage_cache.async_get_cache(key=counter_key, litellm_parent_otel_span=None)
        current_limit = 10
        limit_remaining = current_limit - counter_value if counter_value is not None else current_limit

        rate_limit_data = {
            "model": model,
            "current_limit": current_limit,
            "limit_remaining": limit_remaining,
        }

        return rate_limit_data

    except Exception as e:
        verbose_proxy_logger.error(f"Error getting model per key rate limit info: {e}")
        raise handle_exception_on_proxy(e)