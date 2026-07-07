# Multi-Model AI Routing

SignalFlow supports a primary LLM provider plus optional fallbacks. The existing
Gemini/Claude/OpenAI/Perplexity workflow remains compatible; Qwen, DeepSeek,
GLM, Llama, and Ollama can be enabled without changing API callers.

## Environment

```env
LLM_PROVIDER=gemini
ENABLE_MODEL_ROUTING=true
LLM_FALLBACK_PROVIDERS=claude,openai,qwen,deepseek,ollama

QWEN_API_KEY=
QWEN_MODEL=qwen-plus
QWEN_BASE_URL=

DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=

GLM_API_KEY=
GLM_MODEL=glm-4-flash
GLM_BASE_URL=

LLAMA_API_KEY=
LLAMA_MODEL=llama-3.1-8b-instruct
LLAMA_BASE_URL=

OLLAMA_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3.1
```

Only configured providers are used. A provider is skipped when its required API
key or base URL is missing.

## Usage

Existing calls still work:

```python
from app.services.infrastructure.llm.service import LLMService

llm = LLMService()
text = llm.call_text("Draft a helpful reply")
payload = llm.call_json("Return JSON", '{"topic":"support"}')
```

Route to a specific model family:

```python
text = llm.call_text(
    "Summarize this customer complaint.",
    model_hint="deepseek",
    platform="reddit",
)
```

Generate with legacy mixed sync/async compatibility:

```python
text = llm.generate("Suggest three subreddits")
text_async = await llm.generate("Analyze competitor sentiment")
```

## Fallback Behavior

The router tries:

1. `model_hint`, when provided.
2. The active `LLM_PROVIDER`.
3. `LLM_FALLBACK_PROVIDERS`, when configured.
4. Any other configured provider.

The development-only template fallback is still controlled by
`LLM_ALLOW_TEMPLATE_FALLBACK=true`.

## Prompt Optimization

When `platform` is provided, the router appends small platform guidance to the
system message. It also appends model-family guidance for providers such as
Qwen, DeepSeek, GLM, Llama/Ollama, Claude, Gemini, OpenAI, and Perplexity.
