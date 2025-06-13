from litellm.proxy._types import UserAPIKeyAuth
from litellm.utils import get_secret
from fastapi import Request, HTTPException

async def user_api_key_auth(request: Request, api_key: str) -> UserAPIKeyAuth:
    try:
        master_key = get_secret("LITELLM_MASTER_KEY")

        if api_key == master_key:
            # return UserAPIKeyAuth(api_key=api_key, user_id="admin")
            # return UserAPIKeyAuth(api_key=api_key, user_id="admin", metadata={"model_rpm_limit": {"gemini-2.5-flash": 3}, "model_rph_limit": {"gemini-2.5-flash": 5}, "model_rpd_limit": {"gemini-2.5-flash": 10}})
            return UserAPIKeyAuth(api_key=api_key, user_id="admin", metadata={"model_rpm_limit": {"gemini-2.5-flash": 10}, "model_rpmo_limit": {"gemini-2.5-flash": 500}})
        else:
            raise HTTPException(status_code=401, detail={"error": "Invalid API Key"})
    except Exception as e:
        raise HTTPException(status_code=401, detail={"error": str(e)})