import json
from urllib.parse import urljoin

from fastapi import APIRouter, Body, Depends

from app.dependencies.provider import ProviderContext, ProviderResolver
from app.models.smart_component import SmartChatResponse
from app.schemas.chat import ChatCompletionParam
from app.services.chat import chat_completions

router = APIRouter(
    prefix="/cua",
    tags=["计算机使用代理"],
)

CUA_DEFAULT_MODEL = "doubao-seed-1-8-251228"


@router.post("/chat/stream")
async def cua_chat_stream(
    messages: list[dict] = Body(...),
    provider: ProviderContext = Depends(ProviderResolver("cua")),
):
    llm_params = ChatCompletionParam(
        model=CUA_DEFAULT_MODEL,
        stream=True,
        temperature=0,
        max_tokens=8192,
        messages=messages,
    )

    endpoint = urljoin(provider.base_url + "/", "chat/completions")
    return await chat_completions(llm_params, provider.api_key, endpoint)


@router.post("/chat", response_model=SmartChatResponse)
async def cua_chat(
    messages: list[dict] = Body(...),
    provider: ProviderContext = Depends(ProviderResolver("cua")),
):
    llm_params = ChatCompletionParam(
        model=CUA_DEFAULT_MODEL,
        stream=False,
        temperature=0,
        max_tokens=8192,
        messages=messages,
    )

    endpoint = urljoin(provider.base_url + "/", "chat/completions")
    chat_result = await chat_completions(llm_params, provider.api_key, endpoint)

    return SmartChatResponse(data=json.loads(chat_result.body), code=200, success=True)
