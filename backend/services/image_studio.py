"""
Gemini Ultra Gateway - Image Studio Service
Advanced image generation features like Google Whisk/ImageFX:
- Text to Image
- Image Editing
- Style Mixing / Remix
- Ingredients-based Generation (Subject + Style + Scene)
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
from enum import Enum

from ..core.config import Config, BEIJING_TZ
from ..core.account_pool import Account, get_account_pool
from ..core.session_manager import (
    get_session_manager,
    get_common_headers,
    Session,
)

logger = logging.getLogger("gemini.image_studio")


class IngredientType(str, Enum):
    """Types of ingredients for Whisk-like generation"""
    SUBJECT = "subject"     # What the image is about (person, object)
    STYLE = "style"         # Visual style (painting style, art movement)
    SCENE = "scene"         # Background/environment
    MOOD = "mood"           # Atmosphere/lighting
    REFERENCE = "reference" # General reference image


@dataclass
class ImageIngredient:
    """An ingredient for image generation (like Whisk)"""
    type: IngredientType
    image: Optional[str] = None  # Base64 image data
    prompt: Optional[str] = None  # Text description
    weight: float = 1.0  # Influence weight (0.0 - 1.0)


@dataclass
class ImageGenerationResult:
    """Result of an image generation request"""
    success: bool = False
    image_id: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded
    image_url: Optional[str] = None
    mime_type: str = "image/png"
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ImageEditResult:
    """Result of an image editing request"""
    success: bool = False
    original_image: Optional[str] = None
    edited_image: Optional[str] = None
    edited_image_url: Optional[str] = None
    edit_description: Optional[str] = None
    error: Optional[str] = None


class ImageStudio:
    """
    Advanced Image Generation Studio
    
    Features:
    - text_to_image: Generate image from text prompt
    - edit_image: Edit/modify an existing image
    - remix_image: Apply style from one image to another
    - generate_from_ingredients: Whisk-like generation from multiple ingredients
    """
    
    def __init__(self):
        self._account_pool = get_account_pool()
        self._session_manager = get_session_manager()
        self._http_client = self._account_pool.http_client
        
        # Image generation models
        self.IMAGE_MODELS = [
            "gemini-2.5-flash-image",
            "gemini-2.5-pro-image",
            "gemini-3-pro-preview-image",
            "gemini-3-pro-image",
        ]
        
        # Default model
        self.DEFAULT_MODEL = "gemini-3-pro-preview-image"
        
        # Style presets
        self.STYLE_PRESETS = {
            "photorealistic": "highly detailed photorealistic image, professional photography",
            "anime": "anime style illustration, vibrant colors, clean lines",
            "oil_painting": "classical oil painting style, rich textures, artistic brush strokes",
            "watercolor": "delicate watercolor painting, soft edges, flowing colors",
            "digital_art": "modern digital art, clean and polished, high quality",
            "sketch": "detailed pencil sketch, hand-drawn feel, artistic",
            "3d_render": "3D rendered image, detailed modeling, professional lighting",
            "pixel_art": "retro pixel art style, nostalgic gaming aesthetic",
            "comic": "comic book style, bold lines, dramatic shading",
            "minimalist": "minimalist design, simple shapes, clean composition",
        }
    
    async def text_to_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        style: Optional[str] = None,
        aspect_ratio: str = "1:1",
        quality: str = "high",
        negative_prompt: Optional[str] = None,
        **kwargs,
    ) -> ImageGenerationResult:
        """
        Generate an image from a text prompt
        
        Args:
            prompt: Text description of the image to generate
            model: Model to use (default: gemini-3-pro-preview-image)
            style: Style preset or custom style description
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            quality: Quality level (low, medium, high)
            negative_prompt: What to avoid in the image
            
        Returns:
            ImageGenerationResult with generated image data
        """
        model = model or self.DEFAULT_MODEL
        
        # Build enhanced prompt
        full_prompt = self._build_image_prompt(
            prompt, style, aspect_ratio, quality, negative_prompt
        )
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return ImageGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"img_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Generate image
            result = await self._generate_image(account, session, full_prompt, model)
            
            if result.success and result.image_data:
                image_path = self._save_image(result.image_data, result.mime_type)
                result.image_url = f"/image/{image_path.name}"
                result.metadata["local_path"] = str(image_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Text to image failed: {e}")
            return ImageGenerationResult(success=False, error=str(e))
    
    async def edit_image(
        self,
        image: Union[str, bytes],
        edit_prompt: str,
        model: Optional[str] = None,
        mask: Optional[Union[str, bytes]] = None,
        preserve_style: bool = True,
        **kwargs,
    ) -> ImageEditResult:
        """
        Edit an existing image based on a prompt
        
        Args:
            image: Original image (base64 or bytes)
            edit_prompt: Description of the edit to make
            model: Model to use
            mask: Optional mask for targeted editing
            preserve_style: Whether to preserve the original style
            
        Returns:
            ImageEditResult with edited image
        """
        model = model or self.DEFAULT_MODEL
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return ImageEditResult(success=False, error="No accounts available")
            
            conv_key = f"edit_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Convert image to base64 if bytes
            if isinstance(image, bytes):
                image = base64.b64encode(image).decode()
            
            # Upload original image
            mime_type = self._detect_mime_type(image)
            await self._session_manager.upload_file(account, session, mime_type, image)
            
            # Upload mask if provided
            if mask:
                if isinstance(mask, bytes):
                    mask = base64.b64encode(mask).decode()
                await self._session_manager.upload_file(
                    account, session, "image/png", mask
                )
            
            # Build edit prompt
            full_prompt = f"Edit this image: {edit_prompt}"
            if preserve_style:
                full_prompt += " Maintain the original style and quality."
            
            # Generate edited image
            gen_result = await self._generate_image(account, session, full_prompt, model)
            
            if gen_result.success:
                result = ImageEditResult(
                    success=True,
                    original_image=image[:100] + "...",
                    edited_image=gen_result.image_data,
                    edit_description=edit_prompt,
                )
                
                if gen_result.image_data:
                    image_path = self._save_image(gen_result.image_data, gen_result.mime_type)
                    result.edited_image_url = f"/image/{image_path.name}"
                
                return result
            else:
                return ImageEditResult(success=False, error=gen_result.error)
            
        except Exception as e:
            logger.error(f"Image edit failed: {e}")
            return ImageEditResult(success=False, error=str(e))
    
    async def remix_image(
        self,
        content_image: Union[str, bytes],
        style_image: Union[str, bytes],
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        style_strength: float = 0.7,
        **kwargs,
    ) -> ImageGenerationResult:
        """
        Remix/style transfer - apply style from one image to another
        
        Args:
            content_image: The image to transform
            style_image: The style reference image
            prompt: Optional additional guidance
            model: Model to use
            style_strength: How strongly to apply the style (0.0 - 1.0)
            
        Returns:
            ImageGenerationResult with remixed image
        """
        model = model or self.DEFAULT_MODEL
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return ImageGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"remix_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Convert to base64 if needed
            if isinstance(content_image, bytes):
                content_image = base64.b64encode(content_image).decode()
            if isinstance(style_image, bytes):
                style_image = base64.b64encode(style_image).decode()
            
            # Upload both images
            content_mime = self._detect_mime_type(content_image)
            style_mime = self._detect_mime_type(style_image)
            
            await self._session_manager.upload_file(account, session, content_mime, content_image)
            await self._session_manager.upload_file(account, session, style_mime, style_image)
            
            # Build remix prompt
            strength_desc = "subtle" if style_strength < 0.4 else "moderate" if style_strength < 0.7 else "strong"
            
            full_prompt = (
                f"Apply the visual style, colors, and artistic elements from the second image "
                f"to transform the first image. Apply a {strength_desc} style transfer."
            )
            
            if prompt:
                full_prompt += f" Additional guidance: {prompt}"
            
            # Generate remixed image
            result = await self._generate_image(account, session, full_prompt, model)
            
            if result.success and result.image_data:
                image_path = self._save_image(result.image_data, result.mime_type)
                result.image_url = f"/image/{image_path.name}"
                result.metadata["style_transfer"] = True
                result.metadata["style_strength"] = style_strength
            
            return result
            
        except Exception as e:
            logger.error(f"Image remix failed: {e}")
            return ImageGenerationResult(success=False, error=str(e))
    
    async def generate_from_ingredients(
        self,
        ingredients: List[ImageIngredient],
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        blend_mode: str = "balanced",
        **kwargs,
    ) -> ImageGenerationResult:
        """
        Generate image from multiple ingredients (Whisk-like feature)
        
        This combines multiple reference images and prompts to create
        a new image that incorporates elements from each.
        
        Args:
            ingredients: List of ImageIngredient objects (subject, style, scene, etc.)
            prompt: Optional main prompt to guide generation
            model: Model to use
            blend_mode: How to blend ingredients (balanced, subject_focus, style_focus)
            
        Returns:
            ImageGenerationResult with generated image
        
        Example:
            ingredients = [
                ImageIngredient(type=IngredientType.SUBJECT, image="cat_photo_b64"),
                ImageIngredient(type=IngredientType.STYLE, image="van_gogh_b64"),
                ImageIngredient(type=IngredientType.SCENE, prompt="cozy living room"),
            ]
            result = await studio.generate_from_ingredients(ingredients)
        """
        model = model or self.DEFAULT_MODEL
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return ImageGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"whisk_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Upload ingredient images and build prompt parts
            prompt_parts = []
            uploaded_count = 0
            
            for i, ingredient in enumerate(ingredients):
                type_name = ingredient.type.value
                
                if ingredient.image:
                    # Upload the image
                    if isinstance(ingredient.image, bytes):
                        img_b64 = base64.b64encode(ingredient.image).decode()
                    else:
                        img_b64 = ingredient.image
                    
                    mime_type = self._detect_mime_type(img_b64)
                    await self._session_manager.upload_file(
                        account, session, mime_type, img_b64
                    )
                    uploaded_count += 1
                    
                    weight_desc = "strongly" if ingredient.weight > 0.7 else "moderately" if ingredient.weight > 0.4 else "subtly"
                    prompt_parts.append(
                        f"Use image {uploaded_count} as the {type_name} reference ({weight_desc} influenced)."
                    )
                
                if ingredient.prompt:
                    prompt_parts.append(f"For {type_name}: {ingredient.prompt}")
            
            # Build the main generation prompt
            full_prompt = "Generate an image that combines the following elements:\n"
            full_prompt += "\n".join(prompt_parts)
            
            if prompt:
                full_prompt += f"\n\nMain concept: {prompt}"
            
            # Add blend mode instructions
            if blend_mode == "subject_focus":
                full_prompt += "\nFocus primarily on accurately representing the subject."
            elif blend_mode == "style_focus":
                full_prompt += "\nEmphasize the artistic style over exact subject accuracy."
            else:
                full_prompt += "\nBalance all elements harmoniously."
            
            # Generate image
            result = await self._generate_image(account, session, full_prompt, model)
            
            if result.success and result.image_data:
                image_path = self._save_image(result.image_data, result.mime_type)
                result.image_url = f"/image/{image_path.name}"
                result.metadata["ingredients_count"] = len(ingredients)
                result.metadata["ingredient_types"] = [i.type.value for i in ingredients]
                result.metadata["blend_mode"] = blend_mode
            
            return result
            
        except Exception as e:
            logger.error(f"Ingredients generation failed: {e}")
            return ImageGenerationResult(success=False, error=str(e))
    
    async def _generate_image(
        self,
        account: Account,
        session: Session,
        prompt: str,
        model: str,
    ) -> ImageGenerationResult:
        """Internal method to generate image using Gemini API"""
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
                    "imageGenerationSpec": {},
                },
                "languageCode": "zh-CN",
                "userMetadata": {"timeZone": "Etc/GMT-8"},
                "assistSkippingMode": "REQUEST_ASSIST",
            },
        }
        
        logger.info(f"Generating image with model {model_id}")
        
        response = await self._http_client.post(
            GeminiEndpoints.STREAM_ASSIST,
            headers=headers,
            json=body,
            timeout=120.0,
        )
        
        if response.status_code != 200:
            logger.error(f"Image generation failed: {response.status_code} {response.text}")
            if response.status_code in (401, 403, 429):
                account.mark_quota_error(response.status_code, response.text)
            return ImageGenerationResult(success=False, error=f"API error: {response.status_code}")
        
        account.mark_success()
        
        # Parse response for inline image data
        result = self._parse_image_response(response.text)
        if result.success:
            return result
        
        # If no inline data, check for generated files
        await asyncio.sleep(2)
        files = await self._session_manager.list_session_files(account, session)
        
        for f in files:
            mime_type = f.get("mimeType", "")
            if mime_type.startswith("image/"):
                file_id = f.get("fileId")
                image_data = await self._session_manager.download_file(
                    account, session, file_id
                )
                
                if image_data:
                    return ImageGenerationResult(
                        success=True,
                        image_id=file_id,
                        image_data=base64.b64encode(image_data).decode(),
                        mime_type=mime_type,
                        metadata={"file_info": f},
                    )
        
        return ImageGenerationResult(
            success=False,
            error="Image generation completed but no image found"
        )
    
    def _parse_image_response(self, response_text: str) -> ImageGenerationResult:
        """Parse response text for inline image data"""
        lines = response_text.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith(")]}'"):
                line = line[4:]
            
            if not line:
                continue
            
            try:
                data = json.loads(line)
                reply = data.get("reply", {})
                content = reply.get("groundedContent", {}).get("content", {})
                
                # Check for inline image data
                inline_data = content.get("inlineData", {})
                if inline_data:
                    return ImageGenerationResult(
                        success=True,
                        image_data=inline_data.get("data"),
                        mime_type=inline_data.get("mimeType", "image/png"),
                    )
                
                # Check for file reference
                file_info = content.get("file", {})
                if file_info and file_info.get("mimeType", "").startswith("image/"):
                    return ImageGenerationResult(
                        success=True,
                        image_id=file_info.get("fileId"),
                        mime_type=file_info.get("mimeType", "image/png"),
                        metadata={"needs_download": True},
                    )
                    
            except json.JSONDecodeError:
                continue
        
        return ImageGenerationResult(success=False)
    
    def _build_image_prompt(
        self,
        prompt: str,
        style: Optional[str],
        aspect_ratio: str,
        quality: str,
        negative_prompt: Optional[str],
    ) -> str:
        """Build an enhanced image generation prompt"""
        parts = []
        
        # Add quality indicator
        quality_map = {
            "low": "quick sketch",
            "medium": "good quality",
            "high": "highly detailed, professional quality, masterpiece",
        }
        parts.append(quality_map.get(quality, quality_map["high"]))
        
        # Add style
        if style:
            style_desc = self.STYLE_PRESETS.get(style, style)
            parts.append(style_desc)
        
        # Add main prompt
        parts.append(prompt)
        
        # Add aspect ratio hint
        if aspect_ratio and aspect_ratio != "1:1":
            if aspect_ratio in ("16:9", "4:3"):
                parts.append("wide landscape format")
            elif aspect_ratio in ("9:16", "3:4"):
                parts.append("tall portrait format")
        
        # Add negative prompt
        if negative_prompt:
            parts.append(f"Avoid: {negative_prompt}")
        
        return ", ".join(parts)
    
    def _detect_mime_type(self, b64_data: str) -> str:
        """Detect image MIME type from base64 data"""
        try:
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
        
        return "image/jpeg"
    
    def _save_image(self, b64_data: str, mime_type: str) -> Path:
        """Save image data to cache directory"""
        ext = "png"
        if "jpeg" in mime_type or "jpg" in mime_type:
            ext = "jpg"
        elif "gif" in mime_type:
            ext = "gif"
        elif "webp" in mime_type:
            ext = "webp"
        
        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = Config.IMAGE_SAVE_DIR / filename
        
        image_bytes = base64.b64decode(b64_data)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        logger.info(f"Image saved: {filepath}")
        return filepath
    
    def get_style_presets(self) -> Dict[str, str]:
        """Get available style presets"""
        return self.STYLE_PRESETS.copy()
    
    async def batch_generate(
        self,
        prompts: List[str],
        model: Optional[str] = None,
        style: Optional[str] = None,
        **kwargs,
    ) -> List[ImageGenerationResult]:
        """
        Generate multiple images from a list of prompts
        
        Args:
            prompts: List of text prompts
            model: Model to use
            style: Style preset to apply to all
            
        Returns:
            List of ImageGenerationResult objects
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            logger.info(f"Batch generating image {i+1}/{len(prompts)}")
            result = await self.text_to_image(
                prompt=prompt,
                model=model,
                style=style,
                **kwargs,
            )
            results.append(result)
            
            # Small delay to avoid rate limiting
            if i < len(prompts) - 1:
                await asyncio.sleep(1)
        
        return results
    
    async def generate_variations(
        self,
        image: Union[str, bytes],
        count: int = 4,
        variation_strength: float = 0.5,
        model: Optional[str] = None,
        **kwargs,
    ) -> List[ImageGenerationResult]:
        """
        Generate variations of an existing image
        
        Args:
            image: Source image (base64 or bytes)
            count: Number of variations to generate (1-8)
            variation_strength: How different variations should be (0.0-1.0)
            model: Model to use
            
        Returns:
            List of ImageGenerationResult objects
        """
        model = model or self.DEFAULT_MODEL
        count = min(max(count, 1), 8)  # Clamp to 1-8
        
        results = []
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return [ImageGenerationResult(success=False, error="No accounts available")]
            
            # Convert image to base64 if bytes
            if isinstance(image, bytes):
                image = base64.b64encode(image).decode()
            
            strength_desc = "subtle" if variation_strength < 0.3 else "moderate" if variation_strength < 0.7 else "significant"
            
            for i in range(count):
                conv_key = f"var_{uuid.uuid4().hex[:8]}"
                session = await self._session_manager.get_or_create_session(account, conv_key)
                
                # Upload source image
                mime_type = self._detect_mime_type(image)
                await self._session_manager.upload_file(account, session, mime_type, image)
                
                # Build variation prompt
                prompt = (
                    f"Create variation {i+1} of this image. "
                    f"Make {strength_desc} changes while keeping the core subject. "
                    f"Vary the composition, colors, lighting, or background slightly."
                )
                
                result = await self._generate_image(account, session, prompt, model)
                
                if result.success and result.image_data:
                    image_path = self._save_image(result.image_data, result.mime_type)
                    result.image_url = f"/image/{image_path.name}"
                    result.metadata["variation_number"] = i + 1
                    result.metadata["variation_strength"] = variation_strength
                
                results.append(result)
                
                if i < count - 1:
                    await asyncio.sleep(1)
            
            return results
            
        except Exception as e:
            logger.error(f"Variation generation failed: {e}")
            return [ImageGenerationResult(success=False, error=str(e))]
    
    async def upscale_image(
        self,
        image: Union[str, bytes],
        scale_factor: int = 2,
        model: Optional[str] = None,
        enhance_details: bool = True,
        **kwargs,
    ) -> ImageGenerationResult:
        """
        Upscale an image with AI enhancement
        
        Args:
            image: Source image (base64 or bytes)
            scale_factor: Upscale factor (2 or 4)
            model: Model to use
            enhance_details: Whether to enhance details during upscaling
            
        Returns:
            ImageGenerationResult with upscaled image
        """
        model = model or self.DEFAULT_MODEL
        scale_factor = min(max(scale_factor, 2), 4)
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return ImageGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"upscale_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Convert image to base64 if bytes
            if isinstance(image, bytes):
                image = base64.b64encode(image).decode()
            
            # Upload source image
            mime_type = self._detect_mime_type(image)
            await self._session_manager.upload_file(account, session, mime_type, image)
            
            # Build upscale prompt
            prompt = (
                f"Upscale this image by {scale_factor}x while preserving all details. "
                "Increase the resolution significantly. "
            )
            
            if enhance_details:
                prompt += (
                    "Enhance fine details, sharpen textures, and improve overall clarity. "
                    "Add realistic details where the original is blurry or pixelated."
                )
            else:
                prompt += "Keep the original look, just increase resolution."
            
            result = await self._generate_image(account, session, prompt, model)
            
            if result.success and result.image_data:
                image_path = self._save_image(result.image_data, result.mime_type)
                result.image_url = f"/image/{image_path.name}"
                result.metadata["upscale_factor"] = scale_factor
                result.metadata["enhanced"] = enhance_details
            
            return result
            
        except Exception as e:
            logger.error(f"Image upscaling failed: {e}")
            return ImageGenerationResult(success=False, error=str(e))
    
    async def remove_background(
        self,
        image: Union[str, bytes],
        model: Optional[str] = None,
        output_format: str = "png",
        **kwargs,
    ) -> ImageGenerationResult:
        """
        Remove background from an image
        
        Args:
            image: Source image (base64 or bytes)
            model: Model to use
            output_format: Output format (png recommended for transparency)
            
        Returns:
            ImageGenerationResult with background removed
        """
        model = model or self.DEFAULT_MODEL
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return ImageGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"rembg_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Convert image to base64 if bytes
            if isinstance(image, bytes):
                image = base64.b64encode(image).decode()
            
            # Upload source image
            mime_type = self._detect_mime_type(image)
            await self._session_manager.upload_file(account, session, mime_type, image)
            
            # Build prompt for background removal
            prompt = (
                "Remove the background from this image completely. "
                "Keep only the main subject with a transparent or pure white background. "
                "Ensure clean edges around the subject with no artifacts."
            )
            
            result = await self._generate_image(account, session, prompt, model)
            
            if result.success and result.image_data:
                image_path = self._save_image(result.image_data, "image/png")
                result.image_url = f"/image/{image_path.name}"
                result.metadata["background_removed"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            return ImageGenerationResult(success=False, error=str(e))
    
    async def change_background(
        self,
        image: Union[str, bytes],
        new_background: str,
        model: Optional[str] = None,
        blend_edges: bool = True,
        **kwargs,
    ) -> ImageGenerationResult:
        """
        Change the background of an image
        
        Args:
            image: Source image (base64 or bytes)
            new_background: Description of the new background
            model: Model to use
            blend_edges: Whether to blend edges naturally
            
        Returns:
            ImageGenerationResult with new background
        """
        model = model or self.DEFAULT_MODEL
        
        try:
            account = await self._account_pool.get_next_available()
            if not account:
                return ImageGenerationResult(success=False, error="No accounts available")
            
            conv_key = f"chgbg_{uuid.uuid4().hex[:8]}"
            session = await self._session_manager.get_or_create_session(account, conv_key)
            
            # Convert image to base64 if bytes
            if isinstance(image, bytes):
                image = base64.b64encode(image).decode()
            
            # Upload source image
            mime_type = self._detect_mime_type(image)
            await self._session_manager.upload_file(account, session, mime_type, image)
            
            # Build prompt for background change
            prompt = (
                f"Replace the background of this image with: {new_background}. "
                "Keep the main subject exactly as it is, only change the background. "
            )
            
            if blend_edges:
                prompt += "Blend the edges naturally so the subject looks like it belongs in the new scene."
            
            result = await self._generate_image(account, session, prompt, model)
            
            if result.success and result.image_data:
                image_path = self._save_image(result.image_data, result.mime_type)
                result.image_url = f"/image/{image_path.name}"
                result.metadata["new_background"] = new_background
            
            return result
            
        except Exception as e:
            logger.error(f"Background change failed: {e}")
            return ImageGenerationResult(success=False, error=str(e))


# Global image studio instance
_image_studio: Optional[ImageStudio] = None


def get_image_studio() -> ImageStudio:
    """Get or create the global image studio instance"""
    global _image_studio
    if _image_studio is None:
        _image_studio = ImageStudio()
    return _image_studio
