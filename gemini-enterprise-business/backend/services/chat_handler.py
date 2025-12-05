"""
Gemini Ultra Gateway - Chat Handler
Handles chat completions with streaming support

This module implements the chat completion functionality that interfaces with
the Gemini Business API. It supports both streaming and non-streaming responses,
image/video generation, and multi-turn conversations.
"""

import json
import time
import uuid
import base64
import logging
import asyncio
from typing import Optional, Dict, Any, List, AsyncGenerator, Union
from dataclasses import dataclass

import httpx

from ..core.config import Config, GeminiEndpoints
from ..core.account_pool import Account, get_account_pool
from ..core.session_manager import (
    get_session_manager, 
    get_common_headers,
    Session,
)

logger = logging.getLogger("gemini.chat")


class JSONStreamParser:
    """
    Parser for Google's non-standard/chunked JSON stream responses.
    Can handle truncated JSON objects and implements true streaming parsing.
    """
    def __init__(self):
        self.buffer = ""
        self.decoder = json.JSONDecoder()

    def decode(self, chunk: str) -> List[dict]:
        """Parse chunked JSON data, returns list of complete JSON objects"""
        self.buffer += chunk
        results = []
        while True:
            self.buffer = self.buffer.lstrip()
            # Skip array start [ or separator ,
            if self.buffer.startswith("[") or self.buffer.startswith(","):
                self.buffer = self.buffer[1:]
                continue
            
            if not self.buffer:
                break

            try:
                # Try to parse a complete JSON object
                obj, idx = self.decoder.raw_decode(self.buffer)
                results.append(obj)
                self.buffer = self.buffer[idx:]
            except json.JSONDecodeError:
                # Buffer data incomplete, wait for next chunk
                break
        return results


@dataclass
class ChatImage:
    """Represents a generated or uploaded image"""
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    base64_data: Optional[str] = None
    url: Optional[str] = None
    mime_type: str = "image/png"


@dataclass
class ChatVideo:
    """Represents a generated video"""
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    base64_data: Optional[str] = None
    url: Optional[str] = None
    mime_type: str = "video/mp4"


@dataclass
class ChatResponse:
    """Structured chat response"""
    content: str = ""
    reasoning: str = ""  # Thinking process
    images: List[ChatImage] = None
    videos: List[ChatVideo] = None
    finish_reason: str = "stop"
    usage: Dict[str, int] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.videos is None:
            self.videos = []
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class ChatHandler:
    """Handles chat completions with Gemini Business API"""
    
    def __init__(self):
        self._account_pool = get_account_pool()
        self._session_manager = get_session_manager()
        self._http_client = self._account_pool.http_client
    
    async def chat_completion(
        self,
        messages: List[Dict],
        model: str = "gemini-auto",
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Union[ChatResponse, AsyncGenerator[Dict, None]]:
        """
        Process a chat completion request
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name to use
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            ChatResponse or AsyncGenerator for streaming
        """
        # Get conversation key for session affinity
        conv_key = self._session_manager.get_conversation_key(messages)
        
        # Get account for this conversation
        account = await self._account_pool.get_for_conversation(conv_key)
        if not account:
            raise RuntimeError("No accounts available")
        
        # Get or create session
        session = await self._session_manager.get_or_create_session(account, conv_key)
        
        # Cache session info
        self._account_pool.cache_session(conv_key, session.name, account.name)
        
        # Process any images in messages
        await self._process_message_images(account, session, messages)
        
        # Build the request
        prompt = self._build_prompt(messages)
        
        if stream:
            return self._stream_chat(account, session, prompt, model, temperature, max_tokens)
        else:
            return await self._sync_chat(account, session, prompt, model, temperature, max_tokens)
    
    async def _process_message_images(
        self,
        account: Account,
        session: Session,
        messages: List[Dict],
    ) -> None:
        """Process and upload any images in the messages"""
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "image_url":
                            image_url = part.get("image_url", {})
                            url = image_url.get("url", "")
                            
                            if url.startswith("data:"):
                                # Base64 image
                                mime_type, b64_data = self._parse_data_url(url)
                                file_id = await self._session_manager.upload_file(
                                    account, session, mime_type, b64_data
                                )
                                part["_file_id"] = file_id
                            elif url.startswith("http"):
                                # URL image
                                file_id = await self._session_manager.upload_file_by_url(
                                    account, session, url
                                )
                                part["_file_id"] = file_id
    
    def _parse_data_url(self, data_url: str) -> tuple:
        """Parse a data URL into mime_type and base64 data"""
        if not data_url.startswith("data:"):
            return "application/octet-stream", data_url
        
        parts = data_url.split(",", 1)
        if len(parts) != 2:
            return "application/octet-stream", data_url
        
        header, data = parts
        mime_type = "application/octet-stream"
        
        if ";" in header:
            mime_part = header.split(";")[0]
            if mime_part.startswith("data:"):
                mime_type = mime_part[5:]
        
        return mime_type, data
    
    def _build_prompt(self, messages: List[Dict]) -> str:
        """Build a prompt string from messages"""
        parts = []
        system_prompt = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Handle content as list
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "\n".join(text_parts)
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                parts.append(f"Human: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        
        # Build final prompt
        result = ""
        if system_prompt:
            result = f"<system>\n{system_prompt}\n</system>\n\n"
        
        if parts:
            result += "\n\n".join(parts)
        
        result += "\n\nAssistant:"
        return result
    
    def _build_tools_spec(self, model: str) -> Dict[str, Any]:
        """Build tools specification based on model type"""
        tools_spec = {}
        
        if Config.is_image_model(model):
            tools_spec["imageGenerationSpec"] = {}
        elif Config.is_video_model(model):
            tools_spec["videoGenerationSpec"] = {}
        elif Config.is_search_model(model):
            tools_spec["webGroundingSpec"] = {}
        else:
            # Default: enable all tools
            tools_spec["webGroundingSpec"] = {}
            tools_spec["toolRegistry"] = "default_tool_registry"
            tools_spec["imageGenerationSpec"] = {}
            tools_spec["videoGenerationSpec"] = {}
        
        return tools_spec
    
    async def _sync_chat(
        self,
        account: Account,
        session: Session,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> ChatResponse:
        """Synchronous chat completion"""
        jwt = await account.jwt_mgr.get()
        headers = get_common_headers(jwt)
        
        model_id = Config.get_model_id(model)
        tools_spec = self._build_tools_spec(model)
        
        # Build request body matching Gemini Business API format exactly
        body = {
            "configId": account.config_id,
            "additionalParams": {"token": "-"},
            "streamAssistRequest": {
                "session": session.name,
                "query": {"parts": [{"text": prompt}]},
                "filter": "",
                "fileIds": [],
                "answerGenerationMode": "NORMAL",
                "toolsSpec": tools_spec,
                "languageCode": "zh-CN",
                "userMetadata": {"timeZone": "Etc/GMT-8"},
                "assistSkippingMode": "REQUEST_ASSIST",
            },
        }
        
        # Model ID goes in assistGenerationConfig, not directly
        if model_id and model_id not in ["gemini-video", "gemini-image"]:
            body["streamAssistRequest"]["assistGenerationConfig"] = {
                "modelId": model_id
            }
        
        logger.debug(f"Sending chat request to [{account.name}]")
        
        response = await self._http_client.post(
            GeminiEndpoints.STREAM_ASSIST,
            headers=headers,
            json=body,
        )
        
        if response.status_code != 200:
            logger.error(f"Chat failed [{account.name}]: {response.status_code} {response.text}")
            if response.status_code in (401, 403, 429):
                account.mark_quota_error(response.status_code, response.text)
            raise Exception(f"Chat failed: {response.status_code}")
        
        # Mark success
        account.mark_success()
        
        # Parse response
        return await self._parse_response(account, session, response.text, model)
    
    async def _stream_chat(
        self,
        account: Account,
        session: Session,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> AsyncGenerator[Dict, None]:
        """Streaming chat completion"""
        jwt = await account.jwt_mgr.get()
        headers = get_common_headers(jwt)
        
        model_id = Config.get_model_id(model)
        tools_spec = self._build_tools_spec(model)
        
        # Build request body matching Gemini Business API format exactly
        body = {
            "configId": account.config_id,
            "additionalParams": {"token": "-"},
            "streamAssistRequest": {
                "session": session.name,
                "query": {"parts": [{"text": prompt}]},
                "filter": "",
                "fileIds": [],
                "answerGenerationMode": "NORMAL",
                "toolsSpec": tools_spec,
                "languageCode": "zh-CN",
                "userMetadata": {"timeZone": "Etc/GMT-8"},
                "assistSkippingMode": "REQUEST_ASSIST",
            },
        }
        
        # Model ID goes in assistGenerationConfig, not directly
        if model_id and model_id not in ["gemini-video", "gemini-image"]:
            body["streamAssistRequest"]["assistGenerationConfig"] = {
                "modelId": model_id
            }
        
        logger.debug(f"Starting stream chat to [{account.name}]")
        
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())
        
        full_content = ""
        full_reasoning = ""
        
        async with self._http_client.stream(
            "POST",
            GeminiEndpoints.STREAM_ASSIST,
            headers=headers,
            json=body,
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Stream chat failed: {response.status_code} {error_text}")
                if response.status_code in (401, 403, 429):
                    account.mark_quota_error(response.status_code, error_text.decode())
                raise Exception(f"Stream chat failed: {response.status_code}")
            
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                
                # Process complete JSON objects in buffer
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Remove )]}' prefix if present
                    if line.startswith(")]}'"):
                        line = line[4:]
                    
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        text, reasoning, images = self._extract_content(data)
                        
                        if reasoning:
                            full_reasoning += reasoning
                            # Yield reasoning as a separate chunk
                            yield self._create_chunk(
                                chat_id, created, model,
                                {"reasoning": reasoning},
                                None
                            )
                        
                        if text:
                            full_content += text
                            yield self._create_chunk(
                                chat_id, created, model,
                                {"role": "assistant", "content": text},
                                None
                            )
                    except json.JSONDecodeError:
                        continue
        
        # Final chunk with finish reason
        yield self._create_chunk(
            chat_id, created, model,
            {},
            "stop"
        )
        
        # Check for generated images/videos
        if Config.is_image_model(model) or Config.is_video_model(model):
            await asyncio.sleep(1)  # Wait for file generation
            files = await self._session_manager.list_session_files(account, session)
            
            for f in files:
                file_id = f.get("fileId")
                mime_type = f.get("mimeType", "")
                
                if mime_type.startswith("image/"):
                    data = await self._session_manager.download_file(account, session, file_id)
                    if data:
                        b64 = base64.b64encode(data).decode()
                        yield {
                            "type": "image",
                            "data": b64,
                            "mime_type": mime_type,
                        }
                elif mime_type.startswith("video/"):
                    data = await self._session_manager.download_file(account, session, file_id)
                    if data:
                        b64 = base64.b64encode(data).decode()
                        yield {
                            "type": "video",
                            "data": b64,
                            "mime_type": mime_type,
                        }
        
        # Mark success
        account.mark_success()
    
    def _create_chunk(
        self,
        chat_id: str,
        created: int,
        model: str,
        delta: Dict,
        finish_reason: Optional[str],
    ) -> Dict:
        """Create an OpenAI-compatible streaming chunk"""
        return {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }],
        }
    
    def _extract_content(self, data: Dict) -> tuple:
        """Extract text, reasoning, and images from response data
        
        Handles Gemini Business API response format:
        {
            "streamAssistResponse": {
                "sessionInfo": {...},
                "answer": {
                    "replies": [
                        {
                            "groundedContent": {
                                "content": {"text": "...", "thought": false, ...}
                            }
                        }
                    ]
                },
                "generatedImages": [...]
            }
        }
        """
        text = ""
        reasoning = ""
        images = []
        
        # Handle streamAssistResponse wrapper
        sar = data.get("streamAssistResponse", data)
        
        # Check for generated images at top level
        for gen_img in sar.get("generatedImages", []):
            image_data = gen_img.get("image", {})
            b64_data = image_data.get("bytesBase64Encoded")
            if b64_data:
                images.append(ChatImage(
                    base64_data=b64_data,
                    mime_type=image_data.get("mimeType", "image/png"),
                ))
        
        # Extract from answer.replies
        answer = sar.get("answer", {})
        
        # Check answer level generatedImages
        for gen_img in answer.get("generatedImages", []):
            image_data = gen_img.get("image", {})
            b64_data = image_data.get("bytesBase64Encoded")
            if b64_data:
                images.append(ChatImage(
                    base64_data=b64_data,
                    mime_type=image_data.get("mimeType", "image/png"),
                ))
        
        for reply in answer.get("replies", []):
            # Check reply level generatedImages
            for gen_img in reply.get("generatedImages", []):
                image_data = gen_img.get("image", {})
                b64_data = image_data.get("bytesBase64Encoded")
                if b64_data:
                    images.append(ChatImage(
                        base64_data=b64_data,
                        mime_type=image_data.get("mimeType", "image/png"),
                    ))
            
            gc = reply.get("groundedContent", {})
            content = gc.get("content", {})
            
            # Check if this is a thinking/reasoning response
            thought = content.get("thought", False)
            text_content = content.get("text", "")
            
            if thought:
                reasoning += text_content
            else:
                # Filter out "Image generated by Nano Banana Pro." text
                if text_content and "Image generated by Nano Banana Pro" not in text_content:
                    text += text_content
            
            # Extract inline image data
            inline_data = content.get("inlineData", {})
            if inline_data and inline_data.get("data"):
                images.append(ChatImage(
                    base64_data=inline_data.get("data"),
                    mime_type=inline_data.get("mimeType", "image/png"),
                ))
            
            # Extract file reference
            file_info = content.get("file", {})
            if file_info and file_info.get("fileId"):
                images.append(ChatImage(
                    file_id=file_info.get("fileId"),
                    mime_type=file_info.get("mimeType", "image/png"),
                ))
        
        return text, reasoning, images
    
    async def _parse_response(
        self,
        account: Account,
        session: Session,
        response_text: str,
        model: str,
    ) -> ChatResponse:
        """Parse the full response text into a ChatResponse"""
        result = ChatResponse()
        
        # Split response into JSON lines
        lines = response_text.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove )]}' prefix
            if line.startswith(")]}'"):
                line = line[4:]
            
            if not line:
                continue
            
            try:
                data = json.loads(line)
                text, reasoning, images = self._extract_content(data)
                
                result.content += text
                result.reasoning += reasoning
                result.images.extend(images)
            except json.JSONDecodeError:
                continue
        
        # Download any referenced images
        for img in result.images:
            if img.file_id and not img.base64_data:
                data = await self._session_manager.download_file(
                    account, session, img.file_id
                )
                if data:
                    img.base64_data = base64.b64encode(data).decode()
        
        # Check for generated images/videos if using image/video model
        if Config.is_image_model(model) or Config.is_video_model(model):
            await asyncio.sleep(1)  # Wait for file generation
            files = await self._session_manager.list_session_files(account, session)
            
            for f in files:
                file_id = f.get("fileId")
                mime_type = f.get("mimeType", "")
                
                # Skip already processed files
                if any(img.file_id == file_id for img in result.images):
                    continue
                
                if mime_type.startswith("image/"):
                    data = await self._session_manager.download_file(account, session, file_id)
                    if data:
                        result.images.append(ChatImage(
                            file_id=file_id,
                            base64_data=base64.b64encode(data).decode(),
                            mime_type=mime_type,
                        ))
                elif mime_type.startswith("video/"):
                    data = await self._session_manager.download_file(account, session, file_id)
                    if data:
                        result.videos.append(ChatVideo(
                            file_id=file_id,
                            base64_data=base64.b64encode(data).decode(),
                            mime_type=mime_type,
                        ))
        
        return result


# Global chat handler
_chat_handler: Optional[ChatHandler] = None


def get_chat_handler() -> ChatHandler:
    """Get or create the global chat handler"""
    global _chat_handler
    if _chat_handler is None:
        _chat_handler = ChatHandler()
    return _chat_handler
