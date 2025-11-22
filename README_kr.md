<h1 align="center">
        🚅 LiteLLM
    </h1>
    <p align="center">
        <p align="center">
        <a href="https://render.com/deploy?repo=https://github.com/BerriAI/litellm" target="_blank" rel="nofollow"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render"></a>
        <a href="https://railway.app/template/HLP0Ub?referralCode=jch2ME">
          <img src="https://railway.app/button.svg" alt="Deploy on Railway">
        </a>
        </p>
        <p align="center">OpenAI 형식을 사용하여 모든 LLM API 호출 [Bedrock, Huggingface, VertexAI, TogetherAI, Azure, OpenAI, Groq 등]
        <br>
    </p>
<h4 align="center"><a href="https://docs.litellm.ai/docs/simple_proxy" target="_blank">LiteLLM 프록시 서버 (LLM 게이트웨이)</a> | <a href="https://docs.litellm.ai/docs/hosted" target="_blank"> 호스팅된 프록시 (미리보기)</a> | <a href="https://docs.litellm.ai/docs/enterprise"target="_blank">엔터프라이즈 티어</a></h4>
<h4 align="center">
    <a href="https://pypi.org/project/litellm/" target="_blank">
        <img src="https://img.shields.io/pypi/v/litellm.svg" alt="PyPI Version">
    </a>
    <a href="https://www.ycombinator.com/companies/berriai">
        <img src="https://img.shields.io/badge/Y%20Combinator-W23-orange?style=flat-square" alt="Y Combinator W23">
    </a>
    <a href="https://wa.link/huol9n">
        <img src="https://img.shields.io/static/v1?label=Chat%20on&message=WhatsApp&color=success&logo=WhatsApp&style=flat-square" alt="Whatsapp">
    </a>
    <a href="https://discord.gg/wuPM9dRgDw">
        <img src="https://img.shields.io/static/v1?label=Chat%20on&message=Discord&color=blue&logo=Discord&style=flat-square" alt="Discord">
    </a>
    <a href="https://www.litellm.ai/support">
        <img src="https://img.shields.io/static/v1?label=Chat%20on&message=Slack&color=black&logo=Slack&style=flat-square" alt="Slack">
    </a>
</h4>

LiteLLM은 다음을 관리합니다:

- 입력을 제공자의 `completion`, `embedding`, 및 `image_generation` 엔드포인트로 변환
- [일관된 출력](https://docs.litellm.ai/docs/completion/output), 텍스트 응답은 항상 `['choices'][0]['message']['content']`에서 사용 가능
- 여러 배포(예: Azure/OpenAI)에 걸친 재시도/폴백 로직 - [라우터](https://docs.litellm.ai/docs/routing)
- 프로젝트, API 키, 모델별 예산 및 속도 제한 설정 [LiteLLM 프록시 서버 (LLM 게이트웨이)](https://docs.litellm.ai/docs/simple_proxy)

LiteLLM 성능: 1k RPS에서 **8ms P95 지연 시간** (벤치마크는 [여기](https://docs.litellm.ai/docs/benchmarks) 참조)

[**LiteLLM 프록시 (LLM 게이트웨이) 문서로 이동**](https://github.com/BerriAI/litellm?tab=readme-ov-file#litellm-proxy-server-llm-gateway---docs) <br>
[**지원되는 LLM 제공자로 이동**](https://github.com/BerriAI/litellm?tab=readme-ov-file#supported-providers-docs)

🚨 **안정 릴리스:** `-stable` 태그가 있는 도커 이미지를 사용하세요. 이 이미지들은 게시되기 전에 12시간의 부하 테스트를 거쳤습니다. [릴리스 주기에 대한 자세한 정보는 여기](https://docs.litellm.ai/docs/proxy/release_cycle)

더 많은 제공자를 지원합니다. 제공자나 LLM 플랫폼이 누락된 경우, [기능 요청](https://github.com/BerriAI/litellm/issues/new?assignees=&labels=enhancement&projects=&template=feature_request.yml&title=%5BFeature%5D%3A+)을 제기해 주세요.

# 사용법 ([**문서**](https://docs.litellm.ai/docs/))

> [!IMPORTANT]
> LiteLLM v1.0.0은 이제 `openai>=1.0.0`을 필요로 합니다. 마이그레이션 가이드는 [여기](https://docs.litellm.ai/docs/migration)
> LiteLLM v1.40.14+는 이제 `pydantic>=2.0.0`을 필요로 합니다. 변경 사항은 필요하지 않습니다.

<a target="_blank" href="https://colab.research.google.com/github/BerriAI/litellm/blob/main/cookbook/liteLLM_Getting_Started.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

```shell
pip install litellm
```

```python
from litellm import completion
import os

## 환경 변수 설정
os.environ["OPENAI_API_KEY"] = "your-openai-key"
os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-key"

messages = [{ "content": "Hello, how are you?","role": "user"}]

# openai 호출
response = completion(model="openai/gpt-4o", messages=messages)

# anthropic 호출
response = completion(model="anthropic/claude-sonnet-4-20250514", messages=messages)
print(response)
```

### 응답 (OpenAI 형식)

```json
{
    "id": "chatcmpl-1214900a-6cdd-4148-b663-b5e2f642b4de",
    "created": 1751494488,
    "model": "claude-sonnet-4-20250514",
    "object": "chat.completion",
    "system_fingerprint": null,
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "content": "Hello! I'm doing well, thank you for asking. I'm here and ready to help with whatever you'd like to discuss or work on. How are you doing today?",
                "role": "assistant",
                "tool_calls": null,
                "function_call": null
            }
        }
    ],
    "usage": {
        "completion_tokens": 39,
        "prompt_tokens": 13,
        "total_tokens": 52,
        "completion_tokens_details": null,
        "prompt_tokens_details": {
            "audio_tokens": null,
            "cached_tokens": 0
        },
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0
    }
}
```

제공자가 지원하는 모든 모델을 `model=<provider_name>/<model_name>` 형식으로 호출할 수 있습니다. 제공자별 세부 사항이 있을 수 있으므로 [자세한 내용은 제공자 문서](https://docs.litellm.ai/docs/providers)를 참조하세요.

## 비동기 (Async) ([문서](https://docs.litellm.ai/docs/completion/stream#async-completion))

```python
from litellm import acompletion
import asyncio

async def test_get_response():
    user_message = "Hello, how are you?"
    messages = [{"content": user_message, "role": "user"}]
    response = await acompletion(model="openai/gpt-4o", messages=messages)
    return response

response = asyncio.run(test_get_response())
print(response)
```

## 스트리밍 (Streaming) ([문서](https://docs.litellm.ai/docs/completion/stream))

LiteLLM은 모델 응답 스트리밍을 지원합니다. `stream=True`를 전달하여 응답으로 스트리밍 반복자(iterator)를 받으세요.
스트리밍은 모든 모델(Bedrock, Huggingface, TogetherAI, Azure, OpenAI 등)에서 지원됩니다.

```python
from litellm import completion

messages = [{"content": "Hello, how are you?", "role": "user"}]

# gpt-4o
response = completion(model="openai/gpt-4o", messages=messages, stream=True)
for part in response:
    print(part.choices[0].delta.content or "")

# claude sonnet 4
response = completion('anthropic/claude-sonnet-4-20250514', messages, stream=True)
for part in response:
    print(part)
```

### 응답 청크 (OpenAI 형식)

```json
{
    "id": "chatcmpl-fe575c37-5004-4926-ae5e-bfbc31f356ca",
    "created": 1751494808,
    "model": "claude-sonnet-4-20250514",
    "object": "chat.completion.chunk",
    "system_fingerprint": null,
    "choices": [
        {
            "finish_reason": null,
            "index": 0,
            "delta": {
                "provider_specific_fields": null,
                "content": "Hello",
                "role": "assistant",
                "function_call": null,
                "tool_calls": null,
                "audio": null
            },
            "logprobs": null
        }
    ],
    "provider_specific_fields": null,
    "stream_options": null,
    "citations": null
}
```

## 로깅 관찰 가능성 (Logging Observability) ([문서](https://docs.litellm.ai/docs/observability/callbacks))

LiteLLM은 Lunary, MLflow, Langfuse, DynamoDB, s3 Buckets, Helicone, Promptlayer, Traceloop, Athina, Slack으로 데이터를 전송하기 위한 사전 정의된 콜백을 노출합니다.

```python
from litellm import completion

## 로깅 도구를 위한 환경 변수 설정 (MLflow 사용 시 API 키 설정 필요 없음)
os.environ["LUNARY_PUBLIC_KEY"] = "your-lunary-public-key"
os.environ["HELICONE_API_KEY"] = "your-helicone-auth-key"
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
os.environ["ATHINA_API_KEY"] = "your-athina-api-key"

os.environ["OPENAI_API_KEY"] = "your-openai-key"

# 콜백 설정
litellm.success_callback = ["lunary", "mlflow", "langfuse", "athina", "helicone"] # 입력/출력을 lunary, langfuse, supabase, athina, helicone 등으로 로깅

# openai 호출
response = completion(model="openai/gpt-4o", messages=[{"role": "user", "content": "Hi 👋 - i'm openai"}])
```

# LiteLLM 프록시 서버 (LLM 게이트웨이) - ([문서](https://docs.litellm.ai/docs/simple_proxy))

여러 프로젝트에 걸쳐 지출 추적 + 로드 밸런싱

[호스팅된 프록시 (미리보기)](https://docs.litellm.ai/docs/hosted)

프록시는 다음을 제공합니다:

1. [인증을 위한 훅 (Hooks)](https://docs.litellm.ai/docs/proxy/virtual_keys#custom-auth)
2. [로깅을 위한 훅 (Hooks)](https://docs.litellm.ai/docs/proxy/logging#step-1---create-your-custom-litellm-callback-class)
3. [비용 추적](https://docs.litellm.ai/docs/proxy/virtual_keys#tracking-spend)
4. [속도 제한 (Rate Limiting)](https://docs.litellm.ai/docs/proxy/users#set-rate-limits)

## 📖 프록시 엔드포인트 - [Swagger 문서](https://litellm-api.up.railway.app/)


## 빠른 시작 프록시 - CLI

```shell
pip install 'litellm[proxy]'
```

### 1단계: litellm 프록시 시작

```shell
$ litellm --model huggingface/bigcode/starcoder

#INFO: Proxy running on http://0.0.0.0:4000
```

### 2단계: 프록시에 ChatCompletions 요청 보내기


> [!IMPORTANT]
> 💡 [LiteLLM 프록시를 Langchain (Python, JS), OpenAI SDK (Python, JS), Anthropic SDK, Mistral SDK, LlamaIndex, Instructor, Curl과 함께 사용하기](https://docs.litellm.ai/docs/proxy/user_keys)

```python
import openai # openai v1.0.0+
client = openai.OpenAI(api_key="anything",base_url="http://0.0.0.0:4000") # 프록시를 base_url로 설정
# litellm 프록시에 설정된 모델로 요청 전송, `litellm --model`
response = client.chat.completions.create(model="gpt-3.5-turbo", messages = [
    {
        "role": "user",
        "content": "this is a test request, write a short poem"
    }
])

print(response)
```

## 프록시 키 관리 ([문서](https://docs.litellm.ai/docs/proxy/virtual_keys))

프록시 키를 생성하기 위해 프록시를 Postgres DB와 연결하세요.

```bash
# 코드 가져오기
git clone https://github.com/BerriAI/litellm

# 폴더로 이동
cd litellm

# 마스터 키 추가 - 설정 후 변경 가능
echo 'LITELLM_MASTER_KEY="sk-1234"' > .env

# litellm 솔트(salt) 키 추가 - 모델 추가 후에는 변경 불가
# LLM API 키 자격 증명을 암호화 / 복호화하는 데 사용됨
# 추천 - https://1password.com/password-generator/
# 비밀번호 생성기를 사용하여 litellm 솔트 키를 위한 무작위 해시 생성
echo 'LITELLM_SALT_KEY="sk-1234"' >> .env

source .env

# 시작
docker compose up
```


프록시 서버의 `/ui`에 UI가 있습니다.
![ui_3](https://github.com/BerriAI/litellm/assets/29436595/47c97d5e-b9be-4839-b28c-43d7f4f10033)

여러 프로젝트에 걸쳐 예산 및 속도 제한 설정
`POST /key/generate`

### 요청

```shell
curl 'http://0.0.0.0:4000/key/generate' \
--header 'Authorization: Bearer sk-1234' \
--header 'Content-Type: application/json' \
--data-raw '{"models": ["gpt-3.5-turbo", "gpt-4", "claude-2"], "duration": "20m","metadata": {"user": "ishaan@berri.ai", "team": "core-infra"}}'
```

### 예상 응답

```shell
{
    "key": "sk-kdEXbIqZRwEeEiHwdg7sFA", # Bearer 토큰
    "expires": "2023-11-19T01:38:25.838000+00:00" # datetime 객체
}
```

## 지원되는 제공자 ([웹사이트 지원 모델](https://models.litellm.ai/) | [문서](https://docs.litellm.ai/docs/providers))

| Provider                                                                            | `/chat/completions` | `/messages` | `/responses` | `/embeddings` | `/image/generations` | `/audio/transcriptions` | `/audio/speech` | `/moderations` | `/batches` | `/rerank` |
|-------------------------------------------------------------------------------------|---------------------|-------------|--------------|---------------|----------------------|-------------------------|-----------------|----------------|-----------|-----------|
| [AI/ML API (`aiml`)](https://docs.litellm.ai/docs/providers/aiml) | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |
| [AI21 (`ai21`)](https://docs.litellm.ai/docs/providers/ai21) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [AI21 Chat (`ai21_chat`)](https://docs.litellm.ai/docs/providers/ai21) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Aleph Alpha](https://docs.litellm.ai/docs/providers/aleph_alpha) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Anthropic (`anthropic`)](https://docs.litellm.ai/docs/providers/anthropic) | ✅ | ✅ | ✅ |  |  |  |  |  | ✅ |  |
| [Anthropic Text (`anthropic_text`)](https://docs.litellm.ai/docs/providers/anthropic) | ✅ | ✅ | ✅ |  |  |  |  |  | ✅ |  |
| [Anyscale](https://docs.litellm.ai/docs/providers/anyscale) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [AssemblyAI (`assemblyai`)](https://docs.litellm.ai/docs/pass_through/assembly_ai) | ✅ | ✅ | ✅ |  |  | ✅ |  |  |  |  |
| [Auto Router (`auto_router`)](https://docs.litellm.ai/docs/proxy/auto_routing) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [AWS - Bedrock (`bedrock`)](https://docs.litellm.ai/docs/providers/bedrock) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  | ✅ |
| [AWS - Sagemaker (`sagemaker`)](https://docs.litellm.ai/docs/providers/aws_sagemaker) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |
| [Azure (`azure`)](https://docs.litellm.ai/docs/providers/azure) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |
| [Azure AI (`azure_ai`)](https://docs.litellm.ai/docs/providers/azure_ai) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |
| [Azure Text (`azure_text`)](https://docs.litellm.ai/docs/providers/azure) | ✅ | ✅ | ✅ |  |  | ✅ | ✅ | ✅ | ✅ |  |
| [Baseten (`baseten`)](https://docs.litellm.ai/docs/providers/baseten) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Bytez (`bytez`)](https://docs.litellm.ai/docs/providers/bytez) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Cerebras (`cerebras`)](https://docs.litellm.ai/docs/providers/cerebras) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Clarifai (`clarifai`)](https://docs.litellm.ai/docs/providers/clarifai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Cloudflare AI Workers (`cloudflare`)](https://docs.litellm.ai/docs/providers/cloudflare_workers) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Codestral (`codestral`)](https://docs.litellm.ai/docs/providers/codestral) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Cohere (`cohere`)](https://docs.litellm.ai/docs/providers/cohere) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  | ✅ |
| [Cohere Chat (`cohere_chat`)](https://docs.litellm.ai/docs/providers/cohere) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [CometAPI (`cometapi`)](https://docs.litellm.ai/docs/providers/cometapi) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |
| [CompactifAI (`compactifai`)](https://docs.litellm.ai/docs/providers/compactifai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Custom (`custom`)](https://docs.litellm.ai/docs/providers/custom_llm_server) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Custom OpenAI (`custom_openai`)](https://docs.litellm.ai/docs/providers/openai_compatible) | ✅ | ✅ | ✅ |  |  | ✅ | ✅ | ✅ | ✅ |  |
| [Dashscope (`dashscope`)](https://docs.litellm.ai/docs/providers/dashscope) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Databricks (`databricks`)](https://docs.litellm.ai/docs/providers/databricks) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [DataRobot (`datarobot`)](https://docs.litellm.ai/docs/providers/datarobot) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Deepgram (`deepgram`)](https://docs.litellm.ai/docs/providers/deepgram) | ✅ | ✅ | ✅ |  |  | ✅ |  |  |  |  |
| [DeepInfra (`deepinfra`)](https://docs.litellm.ai/docs/providers/deepinfra) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Deepseek (`deepseek`)](https://docs.litellm.ai/docs/providers/deepseek) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [ElevenLabs (`elevenlabs`)](https://docs.litellm.ai/docs/providers/elevenlabs) | ✅ | ✅ | ✅ |  |  |  | ✅ |  |  |  |
| [Empower (`empower`)](https://docs.litellm.ai/docs/providers/empower) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Fal AI (`fal_ai`)](https://docs.litellm.ai/docs/providers/fal_ai) | ✅ | ✅ | ✅ |  | ✅ |  |  |  |  |  |
| [Featherless AI (`featherless_ai`)](https://docs.litellm.ai/docs/providers/featherless_ai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Fireworks AI (`fireworks_ai`)](https://docs.litellm.ai/docs/providers/fireworks_ai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [FriendliAI (`friendliai`)](https://docs.litellm.ai/docs/providers/friendliai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Galadriel (`galadriel`)](https://docs.litellm.ai/docs/providers/galadriel) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [GitHub Copilot (`github_copilot`)](https://docs.litellm.ai/docs/providers/github_copilot) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [GitHub Models (`github`)](https://docs.litellm.ai/docs/providers/github) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Google - PaLM](https://docs.litellm.ai/docs/providers/palm) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Google - Vertex AI (`vertex_ai`)](https://docs.litellm.ai/docs/providers/vertex) | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |
| [Google AI Studio - Gemini (`gemini`)](https://docs.litellm.ai/docs/providers/gemini) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [GradientAI (`gradient_ai`)](https://docs.litellm.ai/docs/providers/gradient_ai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Groq AI (`groq`)](https://docs.litellm.ai/docs/providers/groq) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Heroku (`heroku`)](https://docs.litellm.ai/docs/providers/heroku) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Hosted VLLM (`hosted_vllm`)](https://docs.litellm.ai/docs/providers/vllm) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Huggingface (`huggingface`)](https://docs.litellm.ai/docs/providers/huggingface) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  | ✅ |
| [Hyperbolic (`hyperbolic`)](https://docs.litellm.ai/docs/providers/hyperbolic) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [IBM - Watsonx.ai (`watsonx`)](https://docs.litellm.ai/docs/providers/watsonx) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |
| [Infinity (`infinity`)](https://docs.litellm.ai/docs/providers/infinity) |  |  |  | ✅ |  |  |  |  |  |  |
| [Jina AI (`jina_ai`)](https://docs.litellm.ai/docs/providers/jina_ai) |  |  |  | ✅ |  |  |  |  |  |  |
| [Lambda AI (`lambda_ai`)](https://docs.litellm.ai/docs/providers/lambda_ai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Lemonade (`lemonade`)](https://docs.litellm.ai/docs/providers/lemonade) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [LiteLLM Proxy (`litellm_proxy`)](https://docs.litellm.ai/docs/providers/litellm_proxy) | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |
| [Llamafile (`llamafile`)](https://docs.litellm.ai/docs/providers/llamafile) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [LM Studio (`lm_studio`)](https://docs.litellm.ai/docs/providers/lm_studio) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Maritalk (`maritalk`)](https://docs.litellm.ai/docs/providers/maritalk) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Meta - Llama API (`meta_llama`)](https://docs.litellm.ai/docs/providers/meta_llama) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Mistral AI API (`mistral`)](https://docs.litellm.ai/docs/providers/mistral) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |
| [Moonshot (`moonshot`)](https://docs.litellm.ai/docs/providers/moonshot) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Morph (`morph`)](https://docs.litellm.ai/docs/providers/morph) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Nebius AI Studio (`nebius`)](https://docs.litellm.ai/docs/providers/nebius) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |
| [NLP Cloud (`nlp_cloud`)](https://docs.litellm.ai/docs/providers/nlp_cloud) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Novita AI (`novita`)](https://novita.ai/models/llm?utm_source=github_litellm&utm_medium=github_readme&utm_campaign=github_link) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Nscale (`nscale`)](https://docs.litellm.ai/docs/providers/nscale) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Nvidia NIM (`nvidia_nim`)](https://docs.litellm.ai/docs/providers/nvidia_nim) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [OCI (`oci`)](https://docs.litellm.ai/docs/providers/oci) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Ollama (`ollama`)](https://docs.litellm.ai/docs/providers/ollama) | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |
| [Ollama Chat (`ollama_chat`)](https://docs.litellm.ai/docs/providers/ollama) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Oobabooga (`oobabooga`)](https://docs.litellm.ai/docs/providers/openai_compatible) | ✅ | ✅ | ✅ |  |  | ✅ | ✅ | ✅ | ✅ |  |
| [OpenAI (`openai`)](https://docs.litellm.ai/docs/providers/openai) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |
| [OpenAI-like (`openai_like`)](https://docs.litellm.ai/docs/providers/openai_compatible) |  |  |  | ✅ |  |  |  |  |  |  |
| [OpenRouter (`openrouter`)](https://docs.litellm.ai/docs/providers/openrouter) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [OVHCloud AI Endpoints (`ovhcloud`)](https://docs.litellm.ai/docs/providers/ovhcloud) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Perplexity AI (`perplexity`)](https://docs.litellm.ai/docs/providers/perplexity) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Petals (`petals`)](https://docs.litellm.ai/docs/providers/petals) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Predibase (`predibase`)](https://docs.litellm.ai/docs/providers/predibase) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Recraft (`recraft`)](https://docs.litellm.ai/docs/providers/recraft) |  |  |  |  | ✅ |  |  |  |  |  |
| [Replicate (`replicate`)](https://docs.litellm.ai/docs/providers/replicate) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Sagemaker Chat (`sagemaker_chat`)](https://docs.litellm.ai/docs/providers/aws_sagemaker) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Sambanova (`sambanova`)](https://docs.litellm.ai/docs/providers/sambanova) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Snowflake (`snowflake`)](https://docs.litellm.ai/docs/providers/snowflake) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Text Completion Codestral (`text-completion-codestral`)](https://docs.litellm.ai/docs/providers/codestral) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Text Completion OpenAI (`text-completion-openai`)](https://docs.litellm.ai/docs/providers/text_completion_openai) | ✅ | ✅ | ✅ |  |  | ✅ | ✅ | ✅ | ✅ |  |
| [Together AI (`together_ai`)](https://docs.litellm.ai/docs/providers/togetherai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Topaz (`topaz`)](https://docs.litellm.ai/docs/providers/topaz) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Triton (`triton`)](https://docs.litellm.ai/docs/providers/triton-inference-server) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [V0 (`v0`)](https://docs.litellm.ai/docs/providers/v0) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Vercel AI Gateway (`vercel_ai_gateway`)](https://docs.litellm.ai/docs/providers/vercel_ai_gateway) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [VLLM (`vllm`)](https://docs.litellm.ai/docs/providers/vllm) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Volcengine (`volcengine`)](https://docs.litellm.ai/docs/providers/volcano) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Voyage AI (`voyage`)](https://docs.litellm.ai/docs/providers/voyage) |  |  |  | ✅ |  |  |  |  |  |  |
| [WandB Inference (`wandb`)](https://docs.litellm.ai/docs/providers/wandb_inference) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Watsonx Text (`watsonx_text`)](https://docs.litellm.ai/docs/providers/watsonx) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [xAI (`xai`)](https://docs.litellm.ai/docs/providers/xai) | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |
| [Xinference (`xinference`)](https://docs.litellm.ai/docs/providers/xinference) |  |  |  | ✅ |  |  |  |  |  |  |

[**문서 읽기**](https://docs.litellm.ai/docs/)

## 개발자 모드에서 실행 (Run in Developer mode)
### 서비스
1. 루트에 .env 파일 설정
2. 의존 서비스 실행 `docker-compose up db prometheus`

### 백엔드
1. (루트에서) uv로 의존성 설치 `uv sync --all-extras`
2. 프록시 백엔드 시작 `uv run python litellm/proxy_cli.py`

### 프론트엔드
1. `ui/litellm-dashboard`로 이동
2. 의존성 설치 `npm install`
3. 대시보드 시작을 위해 `npm run dev` 실행

# 엔터프라이즈 (Enterprise)
더 나은 보안, 사용자 관리 및 전문적인 지원이 필요한 기업을 위해

[창업자와 상담하기](https://calendly.com/d/4mp-gd3-k5k/litellm-1-1-onboarding-chat)

다음이 포함됩니다:
- ✅ **[LiteLLM 상용 라이선스](https://docs.litellm.ai/docs/proxy/enterprise) 하의 기능들:**
- ✅ **기능 우선 순위 지정**
- ✅ **커스텀 통합**
- ✅ **전문 지원 - 전용 디스코드 + 슬랙**
- ✅ **커스텀 SLA**
- ✅ **Single Sign-On을 통한 보안 액세스**

# 기여하기 (Contributing)

LiteLLM에 대한 기여를 환영합니다! 버그 수정, 기능 추가, 문서 개선 등 어떤 것이든 여러분의 도움을 감사히 여깁니다.

## 기여자를 위한 빠른 시작

이 작업은 uv 설치가 필요합니다. [https://astral.sh/uv](https://astral.sh/uv)에서 uv를 설치하세요.

```bash
git clone https://github.com/BerriAI/litellm.git
cd litellm
uv sync --extra dev          # 개발 의존성 설치
uv sync --extra dev --extra proxy --extra proxy-dev  # 프록시를 포함한 모든 의존성 설치
uv run black .               # 코드 포맷팅
uv run ruff check .          # 린트 검사 실행
uv run pytest tests/         # 테스트 실행
```

또는 편리한 단축키를 제공하는 Makefile을 사용할 수 있습니다:
```bash
make install-dev    # 개발 의존성 설치
make format         # 코드 포맷팅
make lint           # 모든 린트 검사 실행
make test-unit      # 단위 테스트 실행
make format-check   # 포맷팅만 확인
```

자세한 기여 가이드라인은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

## 코드 품질 / 린팅 (Code Quality / Linting)

LiteLLM은 [Google Python 스타일 가이드](https://google.github.io/styleguide/pyguide.html)를 따릅니다.

자동화된 검사 항목:
- **Black**: 코드 포맷팅
- **Ruff**: 린팅 및 코드 품질
- **MyPy**: 타입 체크
- **순환 임포트 감지**
- **임포트 안전성 검사**


PR이 병합되기 전에 이 모든 검사를 통과해야 합니다.


# 지원 / 창업자와 대화

- [데모 일정 잡기 👋](https://calendly.com/d/4mp-gd3-k5k/berriai-1-1-onboarding-litellm-hosted-version)
- [커뮤니티 디스코드 💭](https://discord.gg/wuPM9dRgDw)
- [커뮤니티 슬랙 💭](https://www.litellm.ai/support)
- 전화번호 📞 +1 (770) 8783-106 / ‭+1 (412) 618-6238‬
- 이메일 ✉️ ishaan@berri.ai / krrish@berri.ai

# 왜 이것을 만들었나요?

- **단순함의 필요성**: Azure, OpenAI, Cohere 간의 호출을 관리하고 변환하는 코드가 점점 복잡해졌기 때문입니다.

# 기여자 (Contributors)

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

<a href="https://github.com/BerriAI/litellm/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=BerriAI/litellm" />
</a>
