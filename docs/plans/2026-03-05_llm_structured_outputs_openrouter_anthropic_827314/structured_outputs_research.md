# Structured outputs research (LiteLLM × Anthropic × OpenRouter)

Date: 2026-03-05

## What “structured outputs” means here

In this note, **structured outputs** = getting the model to return **valid JSON that conforms to a provided JSON Schema** (often called “JSON schema mode” / “strict schema”).

LiteLLM generally exposes this through the OpenAI-compatible `response_format` parameter:

- **JSON mode** (valid JSON, not schema-validated): `response_format={"type": "json_object"}`
- **Structured outputs / JSON Schema** (canonical shape used by OpenRouter and Anthropic examples): `response_format={"type":"json_schema","json_schema":{"name":"...","strict":true,"schema":{...}}}`
- **Pydantic shortcut**: pass a Pydantic model class as `response_format=MyModel`

Source: LiteLLM “Structured Outputs (JSON Mode)” docs (`https://docs.litellm.ai/docs/completion/json_mode`).

## Anthropic via LiteLLM (direct `anthropic/…`)

### Can LiteLLM do structured outputs for Anthropic?

**Yes, for Anthropic models that support Anthropic’s structured outputs feature.** LiteLLM’s Anthropic provider docs state:

- `response_format` is supported and LiteLLM will automatically:
  - translate OpenAI-style `response_format` into Anthropic’s structured-output request format
  - add the required beta header (`anthropic-beta: structured-outputs-2025-11-13`)
  - internally create/force a tool that matches the schema (implementation detail)

Source: Anthropic provider docs (`https://docs.litellm.ai/docs/providers/anthropic`) → “Structured Outputs”.

### Which Anthropic models are supported (per LiteLLM docs)?

Per the same provider page, LiteLLM explicitly calls out structured outputs support for:

- **Claude Sonnet 4.5**
- **Claude Opus 4.1**
- **Claude Opus 4.5**
- (and in practice, other “Opus 4.x” variants listed on the page may work if Anthropic supports structured outputs for them—use LiteLLM’s capability checks below rather than assuming)

Source: `https://docs.litellm.ai/docs/providers/anthropic` (notes + supported models in “Structured Outputs”).

### How to call it (SDK)

Use `response_format` with `type: "json_schema"`:

```python
from litellm import completion

resp = completion(
    model="anthropic/claude-sonnet-4-5-20250929",
    messages=[{"role": "user", "content": "Return France + capital."}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "capital_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "country": {"type": "string"},
                    "capital": {"type": "string"},
                },
                "required": ["country", "capital"],
                "additionalProperties": False,
            },
        },
    },
)

print(resp.choices[0].message.content)
```

Source: same Anthropic provider doc page (example).

### Anthropic `/v1/messages` passthrough (LiteLLM Proxy)

If you’re calling Anthropic’s **native `/v1/messages`** interface via LiteLLM Proxy, LiteLLM documents Anthropic’s structured outputs under an `output_format` field (native Anthropic style) on `/v1/messages`.

Source: `https://docs.litellm.ai/docs/anthropic_unified/structured_output`.

## OpenRouter via LiteLLM (`openrouter/…`)

### Does OpenRouter support structured outputs?

**Yes.** OpenRouter documents structured outputs using an OpenAI-compatible `response_format` payload:

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "weather",
      "strict": true,
      "schema": { "...": "..." }
    }
  }
}
```

Source: OpenRouter docs (`https://openrouter.ai/docs/guides/features/structured-outputs`).

OpenRouter also notes:

- Support is **model-dependent**
- There’s a filterable models list for `supported_parameters=structured_outputs`
- Structured outputs can be used with streaming (partial JSON that becomes valid JSON when complete)

Source: same OpenRouter docs page.

### Does LiteLLM pass `response_format` through to OpenRouter?

**Yes (current LiteLLM).** Evidence:

- LiteLLM’s “Translated OpenAI params” table includes OpenRouter as a provider that supports OpenAI-style parameters and is expected to reject/strip unsupported params based on `get_supported_openai_params()` (`https://docs.litellm.ai/docs/completion/input#translated-openai-params`).
- A dedicated LiteLLM issue to “Support OpenRouter `response_format`” is marked **closed/completed** (Aug 2025) (`https://github.com/BerriAI/litellm/issues/13438`).

Taken together with OpenRouter’s documented `response_format`, the practical conclusion is: **you can use `response_format` with LiteLLM’s OpenRouter routing, as long as the chosen OpenRouter model supports structured outputs.**

### How to call it (SDK)

Use the same OpenAI-compatible `response_format` you’d use with OpenRouter directly:

```python
from litellm import completion

resp = completion(
    model="openrouter/<openrouter-model-id>",
    messages=[{"role": "user", "content": "Extract {name, email} from: Ada (ada@example.com)."}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "contact",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["name", "email"],
                "additionalProperties": False,
            },
        },
    },
)
print(resp.choices[0].message.content)
```

Notes:

- Replace `openrouter/<openrouter-model-id>` with an id shown on OpenRouter’s models page filtered by `supported_parameters=structured_outputs`.
- You may need to enforce model/provider support in OpenRouter routing (OpenRouter suggests `require_parameters: true` in provider preferences when routing).

Source: OpenRouter structured outputs docs (`https://openrouter.ai/docs/guides/features/structured-outputs`).

## Practical guidance / gotchas

### 1) Model support is the real limiter

- **Anthropic direct**: LiteLLM docs only guarantee Anthropic structured outputs on specific Claude versions (not “all Claude models”).
- **OpenRouter**: structured outputs are supported only for select models; verify on the OpenRouter models page filtered by supported parameters.

### 2) Use capability checks in LiteLLM

LiteLLM documents these checks:

- `litellm.get_supported_openai_params(model=..., custom_llm_provider=...)` to see if `response_format` is supported
- `litellm.supports_response_schema(...)` to see if `json_schema` structured outputs are supported

Source: `https://docs.litellm.ai/docs/completion/json_mode`.

### 3) “JSON mode” isn’t schema mode

`response_format={"type":"json_object"}` generally helps ensure valid JSON, but does **not** guarantee your exact schema. For strict schema adherence, use `type: "json_schema"` + `strict: true` where supported.

Source: LiteLLM JSON mode page (`https://docs.litellm.ai/docs/completion/json_mode`) and OpenRouter structured outputs page.

### 4) Always instruct the model to output JSON

LiteLLM repeats OpenAI’s warning: with JSON mode, if you don’t also instruct the model to output JSON, it can stream whitespace until token limit. This is easy to trip on in production.

Source: `https://docs.litellm.ai/docs/completion/input#translated-openai-params` (response_format description).

### 5) Client-side schema validation fallback exists (but isn’t provider enforcement)

LiteLLM supports a client-side validation flag:

- `litellm.enable_json_schema_validation = True`

This is useful when a provider/model can’t accept the schema natively but you still want guardrails (you’ll need to handle retries/repairs on validation failures in your app).

Source: LiteLLM JSON mode page (`https://docs.litellm.ai/docs/completion/json_mode`).

