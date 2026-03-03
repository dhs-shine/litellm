
# IP Address Filtering

:::info

You need a LiteLLM License to unlock this feature. [Grab time](https://calendly.com/d/4mp-gd3-k5k/litellm-1-1-onboarding-chat), to get one today!

:::

Restrict which IP's can call the proxy endpoints.

```yaml
general_settings:
  allowed_ips: ["192.168.1.1"]
```

**Expected Response** (if IP not listed)

```bash
{
    "error": {
        "message": "Access forbidden: IP address not allowed.",
        "type": "auth_error",
        "param": "None",
        "code": 403
    }
}
```

## Model-specific IP CIDR policies

You can additionally restrict specific models to specific CIDR ranges using `general_settings.model_ip_policies`.

```yaml
general_settings:
  use_x_forwarded_for: true
  model_ip_policies:
    - model: "gpt-4o"
      allow_cidrs: ["10.20.0.0/16", "192.168.100.0/24"]
    - model: "anthropic/*"
      allow_cidrs: ["172.16.0.0/12"]
```

- `model` supports exact match and `*` suffix wildcard patterns.
- If the request model matches a policy and client IP is outside `allow_cidrs`, the request is rejected with HTTP 403.
- For deployments behind reverse proxies, set `use_x_forwarded_for: true` and configure trusted proxy ranges to avoid spoofed `X-Forwarded-For` headers.

