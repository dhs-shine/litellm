import os
from typing import Dict, Optional

from litellm.secret_managers.main import get_secret_str
from litellm.types.utils import StandardCallbackDynamicParams


def initialize_standard_callback_dynamic_params(
    kwargs: Optional[Dict] = None,
) -> StandardCallbackDynamicParams:
    """
    Initialize the standard callback dynamic params from the kwargs

    checks if langfuse_secret_key, gcs_bucket_name in kwargs and sets the corresponding attributes in StandardCallbackDynamicParams
    """

    standard_callback_dynamic_params = StandardCallbackDynamicParams()
    if kwargs:
        _supported_callback_params = (
            StandardCallbackDynamicParams.__annotations__.keys()
        )
        for param in _supported_callback_params:
            if param in kwargs:
                _param_value = kwargs.pop(param)
                if (
                    _param_value is not None
                    and isinstance(_param_value, str)
                    and "os.environ/" in _param_value
                ):
                    _param_value = get_secret_str(secret_name=_param_value)
                standard_callback_dynamic_params[param] = _param_value  # type: ignore

        # New logic for x-application-id
        proxy_server_request = kwargs.get("proxy_server_request")
        if proxy_server_request and hasattr(proxy_server_request, "headers"):
            headers = proxy_server_request.headers
            if headers and hasattr(headers, "get"):
                application_id = headers.get("x-application-id")
                if application_id and isinstance(application_id, str):
                    sanitized_app_id = application_id.replace("-", "_").upper()

                    public_key_env_name = f"{sanitized_app_id}_LANGFUSE_PUBLIC_KEY"
                    secret_key_env_name = f"{sanitized_app_id}_LANGFUSE_SECRET_KEY"
                    host_env_name = f"{sanitized_app_id}_LANGFUSE_HOST"

                    public_key = os.getenv(public_key_env_name)
                    secret_key = os.getenv(secret_key_env_name)
                    host = os.getenv(host_env_name)

                    if public_key:
                        standard_callback_dynamic_params[
                            "langfuse_public_key"
                        ] = public_key
                    if secret_key:
                        standard_callback_dynamic_params[
                            "langfuse_secret_key"
                        ] = secret_key
                    if host:
                        standard_callback_dynamic_params["langfuse_host"] = host

    return standard_callback_dynamic_params
