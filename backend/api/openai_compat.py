"""
Gemini Ultra Gateway - OpenAI Compatible API
Provides OpenAI-compatible endpoints for chat completions
"""

import json
import time
import uuid
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from ..core.config import Config
from ..services.chat_handler import get_chat_handler, ChatResponse

logger = logging.getLogger("gemini.api.openai")

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


# Request/Response Models
class Message(BaseModel):
    role: str
    content: Any  # Can be string or list of content parts
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "gemini-auto"
    messages: List[Message]
    stream: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    user: Optional[str] = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: Optional[Dict] = None
    delta: Optional[Dict] = None
    finish_reason: Optional[str] = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Usage] = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 1700000000
    owned_by: str = "gemini-ultra-gateway"


class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# API Key validation
async def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """Verify API key from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    # Extract bearer token
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    # TODO: Implement actual API key validation against database
    # For now, accept any non-empty token
    if not token:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return token


@router.get("/models", response_model=ModelList)
async def list_models(api_key: str = Depends(verify_api_key)):
    """List available models"""
    models = [
        ModelInfo(id=model_id)
        for model_id in Config.SUPPORTED_MODELS
    ]
    return ModelList(data=models)


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str, api_key: str = Depends(verify_api_key)):
    """Get model information"""
    if model_id not in Config.SUPPORTED_MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return ModelInfo(id=model_id)


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    OpenAI-compatible chat completion endpoint
    
    Supports:
    - Text generation
    - Image generation (with -image models)
    - Video generation (with -video models)
    - Streaming responses
    """
    chat_handler = get_chat_handler()
    
    # Convert messages to dict format
    messages = [msg.model_dump() for msg in request.messages]
    
    try:
        if request.stream:
            # Streaming response
            async def generate():
                async for chunk in await chat_handler.chat_completion(
                    messages=messages,
                    model=request.model,
                    stream=True,
                    temperature=request.temperature or 0.7,
                    max_tokens=request.max_tokens,
                ):
                    # Handle special chunks (images, videos)
                    if isinstance(chunk, dict) and chunk.get("type") in ("image", "video"):
                        # Convert to OpenAI-like format
                        media_chunk = {
                            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": request.model,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "content": f"\n\n![{chunk['type']}](data:{chunk['mime_type']};base64,{chunk['data'][:50]}...)",
                                },
                                "finish_reason": None,
                            }],
                            "_media": {
                                "type": chunk["type"],
                                "mime_type": chunk["mime_type"],
                                "data": chunk["data"],
                            },
                        }
                        yield f"data: {json.dumps(media_chunk)}\n\n"
                    else:
                        yield f"data: {json.dumps(chunk)}\n\n"
                
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            # Non-streaming response
            result: ChatResponse = await chat_handler.chat_completion(
                messages=messages,
                model=request.model,
                stream=False,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens,
            )
            
            # Build response content
            content = result.content
            
            # Add thinking/reasoning if present
            if result.reasoning:
                content = f"<details><summary>Thinking...</summary>\n\n{result.reasoning}\n\n</details>\n\n{content}"
            
            # Add images if present
            for img in result.images:
                if img.base64_data:
                    content += f"\n\n![image](data:{img.mime_type};base64,{img.base64_data})"
                elif img.url:
                    content += f"\n\n![image]({img.url})"
            
            # Add videos if present
            for vid in result.videos:
                if vid.url:
                    content += f"\n\n[Video]({vid.url})"
            
            response = ChatCompletionResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
                created=int(time.time()),
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message={"role": "assistant", "content": content},
                        finish_reason=result.finish_reason,
                    )
                ],
                usage=Usage(**result.usage),
            )
            
            # Add extra fields for images/videos
            response_dict = response.model_dump()
            if result.images:
                response_dict["images"] = [
                    {
                        "file_name": img.file_name,
                        "base64": img.base64_data,
                        "url": img.url,
                        "mime_type": img.mime_type,
                    }
                    for img in result.images
                ]
            if result.videos:
                response_dict["videos"] = [
                    {
                        "file_name": vid.file_name,
                        "base64": vid.base64_data,
                        "url": vid.url,
                        "mime_type": vid.mime_type,
                    }
                    for vid in result.videos
                ]
            
            return JSONResponse(content=response_dict)
            
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    from ..core.account_pool import get_account_pool
    from ..core.session_manager import get_session_manager
    
    pool = get_account_pool()
    sessions = get_session_manager()
    
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "accounts": pool.get_stats(),
        "sessions": sessions.get_stats(),
    }
