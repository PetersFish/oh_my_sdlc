"""opencode-go Promptfoo provider via OpenAI-compatible endpoint.

Usage in promptfooconfig.yaml:
  providers:
    - id: file://path/to/opencode_go_provider.py
      config:
        apiBaseUrl: https://opencode.ai/zen/go/v1
        model: deepseek-v4-pro
        temperature: 0
        max_tokens: 2000
"""

import os
import json
import urllib.request
import urllib.error


def call_api(prompt, options, context):
    config = options.get("config", {})
    api_base_url = config.get("apiBaseUrl", "https://opencode.ai/zen/go/v1")
    model = config.get("model", "deepseek-v4-pro")
    temperature = config.get("temperature", 0)
    max_tokens = config.get("max_tokens", 2000)

    api_key_envar = config.get("apiKeyEnvar", "OPENCODE_GO_API_KEY")
    api_key = os.environ.get(api_key_envar, "")
    if not api_key:
        raise ValueError(f"{api_key_envar} environment variable is not set")

    url = f"{api_base_url}/chat/completions"

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "promptfoo-opencode-provider/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_body = resp.read().decode("utf-8")
            result = json.loads(resp_body)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}"}
    except Exception as e:
        return {"error": f"Provider error: {e}"}

    choices = result.get("choices", [])
    if not choices:
        return {"error": "No choices in response", "raw": json.dumps(result)[:500]}

    message = choices[0].get("message", {})
    content = message.get("content", "")
    reasoning = message.get("reasoning_content", "")

    if not content and not reasoning:
        return {"error": "Empty content in response", "raw": json.dumps(result)[:500]}

    final_output = content if content else reasoning

    return {"output": final_output}
