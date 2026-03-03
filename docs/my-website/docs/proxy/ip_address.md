
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

## Model-level IP Policies

Use `model_ip_policies` to allow a model only from specific IP ranges.

```yaml
general_settings:
  use_x_forwarded_for: true
  mcp_trusted_proxy_ranges: ["10.0.0.0/8"]
  model_ip_policies:
    - model: "gpt-4o"
      allow_cidrs: ["10.20.0.0/16", "192.168.100.0/24"]
    - model: "anthropic/*"
      allow_cidrs: ["172.16.0.0/12"]
```

- `model` supports exact match and wildcard patterns (e.g. `anthropic/*`).
- `allow_cidrs` supports IPv4/IPv6 CIDR values.
- If a request model matches a policy, the client IP must match at least one CIDR in that policy.
- If no policy matches the model, the request is not restricted by `model_ip_policies`.
