"""
Gemini Ultra Gateway - Video Studio Service
Advanced video generation features like Google Flow:
- Text to Video
- Image(s) to Video  
- Video Extension (auto-detect end frame)
- Start Frame to End Frame Interpolation
"""

import json
import time
import uuid
import base64
import logging
import asyncio
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from ..core.config import Config, BEIJING_TZ
from ..core.account_pool import Account, get_account_pool
from ..core.session_manager import (
    get_session_manager,
    get_common_headers,
    Session,
)
from .video_processor import get_video_processor, VideoProcessor

logger = logging.getLogger("gemini.video_studio")


@dataclass
class VideoGenerationResult:
    """Result of a video generation request"""
    success: bool = False
    video_id: Optional[str] = None
    video_data: Optional[str] = None  # Base64 encoded
    video_url: Optional[str] = None
    mime_type: str = "video/mp4"
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoExtensionResult:
    """Result of a video extension request"""
    success: bool = False
    original_video_url: Optional[str] = None
    extended_video_data: Optional[str] = None  # Base64 encoded
    extended_video_url: Optional[str] = None
    last_frame_used: Optional[str] = None  # Base64 of extracted last frame
    extension_duration: Optional[float] = None
    total_duration: Optional[float] = None
    error: Optional[str] = None


class VideoStudio:
    """
    Advanced Video Generation Studio
    
    Features:
    - text_to_video: Generate video from text prompt
    - images_to_video: Generate video from one or more images
    - extend_video: Extend an existing video (Flow-like feature)
    - interpolate_frames: Generate video between start and end frames
    """
    
    def __init__(self):
        self._account_pool = get_account_pool()
        self._session_manager = get_session_manager()
        self._http_client = self._account_pool.http_client
        self._processor = get_video_processor()
        
        # Video generation models
        self.VIDEO_MODELS = [
            "gemini-2.5-flash-video",
            "gemini-2.5-pro-video",
            "gemini-3-pro-preview-video",
            "gemini-3-pro-video",
        ]
        
        # Default model for video generation
        self.DEFAULT_MODEL = "gemini-3-pro-preview-video"
    
    @property
    def processor(self) -> VideoProcessor:
        """Get the video processor instance"""
        return self._processor
    
    async def text_to_video(
        self,
        prompt: str,
        model: Optional[str] = None,
        duration: int = 5,
        style: Optional[str] = None,
        aspect_ratio: str = "16:9",
        **kwargs,
    ) -> VideoGenerationResult:
        """
        Generate a video from a text prompt
        
        Args:
            prompt: Text description of the video to generate
            model: Model to use (default: gemini-3-pro-preview-video)
            duration: Target duration in seconds (approximate)
            style: Optional style modifier (cinematic, anime, realistic, etc.)
            aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
            
        Returns:
            VideoGenerationResult with generated video data
        """
        model = model or self.DEFAULT_MODEL
        
        # Build enhanced prompt
        full_prompt = self._build_video_prompt(prompt, style, duration, aspect_ratio)
        
        try:
            # Get account and session
            account = await self._account_pool.get_next_available()
            if not account:
                return VideoGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"video_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Send video generation request
            result = await self._generate_video(account, session, full_prompt, model)
            
            if result.success:
                # Save video to cache
                if result.video_data:
                    video_path = self._save_video(result.video_data, result.mime_type)
                    result.video_url = f"/video/{video_path.name}"
                    result.metadata["local_path"] = str(video_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Text to video failed: {e}")
            return VideoGenerationResult(success=False, error=str(e))
    
    async def images_to_video(
        self,
        images: List[Union[str, bytes]],
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        duration: int = 5,
        transition_style: str = "smooth",
        **kwargs,
    ) -> VideoGenerationResult:
        """
        Generate a video from one or more images (like Flow's image-to-video)
        
        Args:
            images: List of images (base64 strings or bytes)
            prompt: Optional text prompt to guide the video generation
            model: Model to use
            duration: Target duration in seconds
            transition_style: How to transition between images (smooth, morph, cut)
            
        Returns:
            VideoGenerationResult with generated video data
        """
        model = model or self.DEFAULT_MODEL
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return VideoGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"img2vid_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Upload images to session
            file_ids = []
            for i, img in enumerate(images):
                if isinstance(img, bytes):
                    img = base64.b64encode(img).decode()
                
                # Detect mime type from base64
                mime_type = self._detect_image_mime(img)
                
                file_id = await self._session_manager.upload_file(
                    account, session, mime_type, img
                )
                file_ids.append(file_id)
                logger.info(f"Uploaded image {i+1}/{len(images)}: {file_id}")
            
            # Build prompt
            if prompt:
                full_prompt = f"Create a {duration} second video from the uploaded images. {prompt}"
            else:
                full_prompt = f"Create a smooth {duration} second video animation from the uploaded images with {transition_style} transitions."
            
            if len(images) == 1:
                full_prompt = f"Animate this image into a {duration} second video. Add natural motion and bring it to life."
                if prompt:
                    full_prompt += f" {prompt}"
            
            # Generate video
            result = await self._generate_video(account, session, full_prompt, model)
            
            if result.success and result.video_data:
                video_path = self._save_video(result.video_data, result.mime_type)
                result.video_url = f"/video/{video_path.name}"
                result.metadata["local_path"] = str(video_path)
                result.metadata["source_images"] = len(images)
            
            return result
            
        except Exception as e:
            logger.error(f"Images to video failed: {e}")
            return VideoGenerationResult(success=False, error=str(e))
    
    async def extend_video(
        self,
        video: Union[str, bytes],
        extension_duration: int = 5,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        auto_detect_end_frame: bool = True,
        concatenate: bool = False,
        **kwargs,
    ) -> VideoExtensionResult:
        """
        Extend an existing video (like Google Flow's video extension)
        
        This automatically extracts the last frame of the video and generates
        a continuation that seamlessly extends the original.
        
        Args:
            video: Video data (base64 string or bytes)
            extension_duration: How many seconds to add
            prompt: Optional prompt to guide the extension
            model: Model to use
            auto_detect_end_frame: Automatically extract last frame for better continuation
            concatenate: Whether to concatenate original + extension (requires FFmpeg)
            
        Returns:
            VideoExtensionResult with extended video
        """
        model = model or self.DEFAULT_MODEL
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return VideoExtensionResult(success=False, error="No accounts available")
            
            conv_key = f"extend_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Convert video to base64 if bytes
            if isinstance(video, bytes):
                video_b64 = base64.b64encode(video).decode()
            else:
                video_b64 = video
            
            # Save original video temporarily for processing
            original_path = None
            last_frame_b64 = None
            
            if auto_detect_end_frame and self._processor.has_ffmpeg:
                # Save video temporarily to extract last frame
                original_path = Config.VIDEO_SAVE_DIR / f"original_{uuid.uuid4().hex[:8]}.mp4"
                video_bytes = base64.b64decode(video_b64)
                with open(original_path, "wb") as f:
                    f.write(video_bytes)
                
                # Extract last frame
                last_frame = self._processor.extract_last_frame(original_path)
                if last_frame:
                    last_frame_b64 = self._processor.frame_to_base64(last_frame)
                    logger.info(f"Extracted last frame from video for better continuation")
                    
                    # Upload last frame as reference
                    await self._session_manager.upload_file(
                        account, session, last_frame.mime_type, last_frame_b64
                    )
            
            # Upload original video
            video_mime = self._detect_video_mime(video_b64)
            await self._session_manager.upload_file(
                account, session, video_mime, video_b64
            )
            
            # Build extension prompt
            if prompt:
                full_prompt = f"Continue this video for {extension_duration} more seconds. {prompt}"
            else:
                full_prompt = (
                    f"Continue this video seamlessly for {extension_duration} more seconds. "
                    "Maintain the same style, motion, and subject. "
                    "The extension should flow naturally from the last frame."
                )
            
            if last_frame_b64:
                full_prompt += " Use the uploaded last frame as the starting point for the continuation."
            
            # Generate extension
            gen_result = await self._generate_video(account, session, full_prompt, model)
            
            if gen_result.success:
                result = VideoExtensionResult(
                    success=True,
                    extended_video_data=gen_result.video_data,
                    extension_duration=extension_duration,
                    last_frame_used=last_frame_b64,
                )
                
                if gen_result.video_data:
                    extension_path = self._save_video(gen_result.video_data, gen_result.mime_type)
                    result.extended_video_url = f"/video/{extension_path.name}"
                    
                    # Optionally concatenate original + extension
                    if concatenate and original_path and self._processor.has_ffmpeg:
                        concat_path = Config.VIDEO_SAVE_DIR / f"concat_{uuid.uuid4().hex[:8]}.mp4"
                        success = self._processor.concatenate_videos(
                            [original_path, extension_path],
                            concat_path,
                            crossfade_duration=0.5,  # Smooth transition
                        )
                        
                        if success:
                            result.extended_video_url = f"/video/{concat_path.name}"
                            result.extended_video_data = self._processor.video_to_base64(concat_path)
                            logger.info(f"Concatenated original + extension: {concat_path}")
                
                # Get video info
                if original_path:
                    video_info = self._processor.get_video_info(original_path)
                    if video_info:
                        result.total_duration = video_info.duration + extension_duration
                        result.original_video_url = f"/video/{original_path.name}"
                
                return result
            else:
                return VideoExtensionResult(success=False, error=gen_result.error)
            
        except Exception as e:
            logger.error(f"Video extension failed: {e}")
            return VideoExtensionResult(success=False, error=str(e))
    
    async def interpolate_frames(
        self,
        start_frame: Union[str, bytes],
        end_frame: Union[str, bytes],
        duration: int = 3,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        interpolation_style: str = "smooth",
        **kwargs,
    ) -> VideoGenerationResult:
        """
        Generate a video that transitions from start frame to end frame
        (Similar to Flow's start-to-end frame feature)
        
        Args:
            start_frame: Starting image (base64 or bytes)
            end_frame: Ending image (base64 or bytes)
            duration: Duration of the transition in seconds
            prompt: Optional prompt to guide the interpolation
            model: Model to use
            interpolation_style: Style of interpolation (smooth, morph, cinematic)
            
        Returns:
            VideoGenerationResult with interpolated video
        """
        model = model or self.DEFAULT_MODEL
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return VideoGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"interp_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Convert frames to base64 if bytes
            if isinstance(start_frame, bytes):
                start_frame = base64.b64encode(start_frame).decode()
            if isinstance(end_frame, bytes):
                end_frame = base64.b64encode(end_frame).decode()
            
            # Upload both frames
            start_mime = self._detect_image_mime(start_frame)
            end_mime = self._detect_image_mime(end_frame)
            
            start_id = await self._session_manager.upload_file(
                account, session, start_mime, start_frame
            )
            end_id = await self._session_manager.upload_file(
                account, session, end_mime, end_frame
            )
            
            logger.info(f"Uploaded frames: start={start_id}, end={end_id}")
            
            # Build interpolation prompt
            base_prompt = (
                f"Create a {duration} second video that smoothly transitions from the first "
                f"image to the second image. Use {interpolation_style} motion and natural "
                "movement to connect the two frames."
            )
            
            if prompt:
                full_prompt = f"{base_prompt} Additional guidance: {prompt}"
            else:
                full_prompt = base_prompt
            
            # Generate video
            result = await self._generate_video(account, session, full_prompt, model)
            
            if result.success and result.video_data:
                video_path = self._save_video(result.video_data, result.mime_type)
                result.video_url = f"/video/{video_path.name}"
                result.metadata["local_path"] = str(video_path)
                result.metadata["interpolation_type"] = "frame_to_frame"
            
            return result
            
        except Exception as e:
            logger.error(f"Frame interpolation failed: {e}")
            return VideoGenerationResult(success=False, error=str(e))
    
    async def _generate_video(
        self,
        account: Account,
        session: Session,
        prompt: str,
        model: str,
    ) -> VideoGenerationResult:
        """Internal method to generate video using Gemini API"""
        from ..core.config import GeminiEndpoints
        
        jwt = await account.jwt_mgr.get()
        headers = get_common_headers(jwt)
        
        model_id = Config.get_model_id(model)
        
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
                "toolsSpec": {
                    "videoGenerationSpec": {},
                },
                "languageCode": "zh-CN",
                "userMetadata": {"timeZone": "Etc/GMT-8"},
                "assistSkippingMode": "REQUEST_ASSIST",
            },
        }
        
        logger.info(f"Generating video with model {model_id}")
        
        from ..core.config import GeminiEndpoints
        
        response = await self._http_client.post(
            GeminiEndpoints.STREAM_ASSIST,
            headers=headers,
            json=body,
            timeout=300.0,  # Video generation takes longer
        )
        
        if response.status_code != 200:
            logger.error(f"Video generation failed: {response.status_code} {response.text}")
            if response.status_code in (401, 403, 429):
                account.mark_quota_error(response.status_code, response.text)
            return VideoGenerationResult(success=False, error=f"API error: {response.status_code}")
        
        account.mark_success()
        
        # Wait for video to be generated and available
        await asyncio.sleep(3)
        
        # List generated files
        files = await self._session_manager.list_session_files(account, session)
        
        for f in files:
            mime_type = f.get("mimeType", "")
            if mime_type.startswith("video/"):
                file_id = f.get("fileId")
                video_data = await self._session_manager.download_file(
                    account, session, file_id
                )
                
                if video_data:
                    return VideoGenerationResult(
                        success=True,
                        video_id=file_id,
                        video_data=base64.b64encode(video_data).decode(),
                        mime_type=mime_type,
                        metadata={"file_info": f},
                    )
        
        return VideoGenerationResult(
            success=False,
            error="Video generation completed but no video file found"
        )
    
    def _build_video_prompt(
        self,
        prompt: str,
        style: Optional[str],
        duration: int,
        aspect_ratio: str,
    ) -> str:
        """Build an enhanced video generation prompt"""
        parts = [f"Generate a {duration} second video:"]
        
        if style:
            parts.append(f"Style: {style}")
        
        if aspect_ratio:
            parts.append(f"Aspect ratio: {aspect_ratio}")
        
        parts.append(f"Content: {prompt}")
        
        return " ".join(parts)
    
    def _detect_image_mime(self, b64_data: str) -> str:
        """Detect image MIME type from base64 data"""
        try:
            # Check first few bytes after decoding
            header = base64.b64decode(b64_data[:32])
            
            if header.startswith(b'\x89PNG'):
                return "image/png"
            elif header.startswith(b'\xff\xd8\xff'):
                return "image/jpeg"
            elif header.startswith(b'GIF8'):
                return "image/gif"
            elif header.startswith(b'RIFF') and b'WEBP' in header:
                return "image/webp"
        except:
            pass
        
        return "image/jpeg"  # Default
    
    def _detect_video_mime(self, b64_data: str) -> str:
        """Detect video MIME type from base64 data"""
        try:
            header = base64.b64decode(b64_data[:32])
            
            if b'ftyp' in header:
                return "video/mp4"
            elif header.startswith(b'\x1a\x45\xdf\xa3'):
                return "video/webm"
        except:
            pass
        
        return "video/mp4"  # Default
    
    def _save_video(self, b64_data: str, mime_type: str) -> Path:
        """Save video data to cache directory"""
        ext = "mp4"
        if "webm" in mime_type:
            ext = "webm"
        elif "quicktime" in mime_type or "mov" in mime_type:
            ext = "mov"
        
        filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = Config.VIDEO_SAVE_DIR / filename
        
        video_bytes = base64.b64decode(b64_data)
        with open(filepath, "wb") as f:
            f.write(video_bytes)
        
        logger.info(f"Video saved: {filepath}")
        return filepath


# Global video studio instance
_video_studio: Optional[VideoStudio] = None


def get_video_studio() -> VideoStudio:
    """Get or create the global video studio instance"""
    global _video_studio
    if _video_studio is None:
        _video_studio = VideoStudio()
    return _video_studio
