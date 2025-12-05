"""
Gemini Ultra Gateway - Media Studio API
Advanced endpoints for image and video generation (Flow/Whisk-like)
"""

import json
import time
import uuid
import base64
import logging
from typing import Optional, Dict, Any, List, Union

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from ..core.config import Config
from ..services.image_studio import (
    get_image_studio,
    ImageIngredient,
    IngredientType,
    ImageGenerationResult,
)
from ..services.video_studio import (
    get_video_studio,
    VideoGenerationResult,
    VideoExtensionResult,
)

logger = logging.getLogger("gemini.api.media")

router = APIRouter(prefix="/v1", tags=["Media Studio"])


# ============== Request Models ==============

class TextToImageRequest(BaseModel):
    """Request for text-to-image generation"""
    prompt: str
    model: Optional[str] = None
    style: Optional[str] = None
    aspect_ratio: str = "1:1"
    quality: str = "high"
    negative_prompt: Optional[str] = None


class ImageEditRequest(BaseModel):
    """Request for image editing"""
    image: str  # Base64 encoded image
    edit_prompt: str
    model: Optional[str] = None
    mask: Optional[str] = None  # Base64 encoded mask
    preserve_style: bool = True


class ImageRemixRequest(BaseModel):
    """Request for image style remix"""
    content_image: str  # Base64 encoded
    style_image: str  # Base64 encoded
    prompt: Optional[str] = None
    model: Optional[str] = None
    style_strength: float = 0.7


class IngredientModel(BaseModel):
    """Single ingredient for Whisk-like generation"""
    type: str  # subject, style, scene, mood, reference
    image: Optional[str] = None  # Base64 encoded
    prompt: Optional[str] = None
    weight: float = 1.0


class IngredientsGenerateRequest(BaseModel):
    """Request for ingredients-based generation (Whisk-like)"""
    ingredients: List[IngredientModel]
    prompt: Optional[str] = None
    model: Optional[str] = None
    blend_mode: str = "balanced"


class TextToVideoRequest(BaseModel):
    """Request for text-to-video generation"""
    prompt: str
    model: Optional[str] = None
    duration: int = 5
    style: Optional[str] = None
    aspect_ratio: str = "16:9"


class ImagesToVideoRequest(BaseModel):
    """Request for images-to-video generation"""
    images: List[str]  # List of base64 encoded images
    prompt: Optional[str] = None
    model: Optional[str] = None
    duration: int = 5
    transition_style: str = "smooth"


class VideoExtendRequest(BaseModel):
    """Request for video extension (Flow-like)"""
    video: str  # Base64 encoded video
    extension_duration: int = 5
    prompt: Optional[str] = None
    model: Optional[str] = None


class FrameInterpolateRequest(BaseModel):
    """Request for frame-to-frame interpolation"""
    start_frame: str  # Base64 encoded image
    end_frame: str  # Base64 encoded image
    duration: int = 3
    prompt: Optional[str] = None
    model: Optional[str] = None
    interpolation_style: str = "smooth"


class BatchImageRequest(BaseModel):
    """Request for batch image generation"""
    prompts: List[str]
    model: Optional[str] = None
    style: Optional[str] = None


class ImageVariationsRequest(BaseModel):
    """Request for generating image variations"""
    image: str  # Base64 encoded
    count: int = 4
    variation_strength: float = 0.5
    model: Optional[str] = None


class ImageUpscaleRequest(BaseModel):
    """Request for image upscaling"""
    image: str  # Base64 encoded
    scale_factor: int = 2  # 2 or 4
    model: Optional[str] = None
    enhance_details: bool = True


class RemoveBackgroundRequest(BaseModel):
    """Request for background removal"""
    image: str  # Base64 encoded
    model: Optional[str] = None


class ChangeBackgroundRequest(BaseModel):
    """Request for background change"""
    image: str  # Base64 encoded
    new_background: str  # Description of new background
    model: Optional[str] = None
    blend_edges: bool = True


class VideoExtendAdvancedRequest(BaseModel):
    """Request for advanced video extension"""
    video: str  # Base64 encoded video
    extension_duration: int = 5
    prompt: Optional[str] = None
    model: Optional[str] = None
    auto_detect_end_frame: bool = True
    concatenate: bool = False


# ============== Response Models ==============

class ImageResponse(BaseModel):
    """Standard image generation response"""
    success: bool
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    image_data: Optional[str] = None  # Base64
    mime_type: str = "image/png"
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class VideoResponse(BaseModel):
    """Standard video generation response"""
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    video_data: Optional[str] = None  # Base64
    mime_type: str = "video/mp4"
    duration: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ============== API Key Validation ==============

async def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """Verify API key from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    if not token:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return token


# ============== Image Studio Endpoints ==============

@router.post("/image/generate", response_model=ImageResponse)
async def generate_image(
    request: TextToImageRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate an image from a text prompt
    
    Similar to Google ImageFX / DALL-E
    """
    studio = get_image_studio()
    
    try:
        result = await studio.text_to_image(
            prompt=request.prompt,
            model=request.model,
            style=request.style,
            aspect_ratio=request.aspect_ratio,
            quality=request.quality,
            negative_prompt=request.negative_prompt,
        )
        
        return ImageResponse(
            success=result.success,
            image_id=result.image_id,
            image_url=result.image_url,
            image_data=result.image_data,
            mime_type=result.mime_type,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/edit", response_model=ImageResponse)
async def edit_image(
    request: ImageEditRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Edit an existing image based on a prompt
    
    Upload an image and describe the edit you want to make.
    """
    studio = get_image_studio()
    
    try:
        result = await studio.edit_image(
            image=request.image,
            edit_prompt=request.edit_prompt,
            model=request.model,
            mask=request.mask,
            preserve_style=request.preserve_style,
        )
        
        return ImageResponse(
            success=result.success,
            image_url=result.edited_image_url,
            image_data=result.edited_image,
            error=result.error,
            metadata={"edit_description": result.edit_description},
        )
    except Exception as e:
        logger.error(f"Image edit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/remix", response_model=ImageResponse)
async def remix_image(
    request: ImageRemixRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Apply the style from one image to another (style transfer)
    
    Provide a content image and a style reference image.
    """
    studio = get_image_studio()
    
    try:
        result = await studio.remix_image(
            content_image=request.content_image,
            style_image=request.style_image,
            prompt=request.prompt,
            model=request.model,
            style_strength=request.style_strength,
        )
        
        return ImageResponse(
            success=result.success,
            image_id=result.image_id,
            image_url=result.image_url,
            image_data=result.image_data,
            mime_type=result.mime_type,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Image remix failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/from-ingredients", response_model=ImageResponse)
async def generate_from_ingredients(
    request: IngredientsGenerateRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate an image from multiple ingredients (Whisk-like)
    
    Combine subject, style, scene, and mood references to create
    a unique image that incorporates elements from each.
    
    Example:
    ```json
    {
        "ingredients": [
            {"type": "subject", "image": "base64_cat_photo..."},
            {"type": "style", "image": "base64_van_gogh_painting..."},
            {"type": "scene", "prompt": "cozy living room with fireplace"}
        ],
        "prompt": "A cat relaxing",
        "blend_mode": "balanced"
    }
    ```
    """
    studio = get_image_studio()
    
    try:
        # Convert request ingredients to ImageIngredient objects
        ingredients = [
            ImageIngredient(
                type=IngredientType(ing.type),
                image=ing.image,
                prompt=ing.prompt,
                weight=ing.weight,
            )
            for ing in request.ingredients
        ]
        
        result = await studio.generate_from_ingredients(
            ingredients=ingredients,
            prompt=request.prompt,
            model=request.model,
            blend_mode=request.blend_mode,
        )
        
        return ImageResponse(
            success=result.success,
            image_id=result.image_id,
            image_url=result.image_url,
            image_data=result.image_data,
            mime_type=result.mime_type,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Ingredients generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/styles")
async def get_style_presets(api_key: str = Depends(verify_api_key)):
    """Get available style presets for image generation"""
    studio = get_image_studio()
    return {"styles": studio.get_style_presets()}


@router.post("/image/batch")
async def batch_generate_images(
    request: BatchImageRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate multiple images from a list of prompts
    
    Useful for batch processing or generating series of related images.
    """
    studio = get_image_studio()
    
    try:
        results = await studio.batch_generate(
            prompts=request.prompts,
            model=request.model,
            style=request.style,
        )
        
        return {
            "success": True,
            "count": len(results),
            "images": [
                {
                    "success": r.success,
                    "image_url": r.image_url,
                    "image_data": r.image_data,
                    "error": r.error,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Batch generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/variations")
async def generate_image_variations(
    request: ImageVariationsRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate variations of an existing image
    
    Upload an image and get multiple unique variations.
    """
    studio = get_image_studio()
    
    try:
        results = await studio.generate_variations(
            image=request.image,
            count=request.count,
            variation_strength=request.variation_strength,
            model=request.model,
        )
        
        return {
            "success": True,
            "count": len(results),
            "variations": [
                {
                    "success": r.success,
                    "image_url": r.image_url,
                    "image_data": r.image_data,
                    "variation_number": r.metadata.get("variation_number"),
                    "error": r.error,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Variation generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/upscale", response_model=ImageResponse)
async def upscale_image(
    request: ImageUpscaleRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Upscale an image with AI enhancement
    
    Increase resolution by 2x or 4x while enhancing details.
    """
    studio = get_image_studio()
    
    try:
        result = await studio.upscale_image(
            image=request.image,
            scale_factor=request.scale_factor,
            model=request.model,
            enhance_details=request.enhance_details,
        )
        
        return ImageResponse(
            success=result.success,
            image_id=result.image_id,
            image_url=result.image_url,
            image_data=result.image_data,
            mime_type=result.mime_type,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Image upscale failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/remove-background", response_model=ImageResponse)
async def remove_background(
    request: RemoveBackgroundRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Remove the background from an image
    
    Returns the subject with a transparent or white background.
    """
    studio = get_image_studio()
    
    try:
        result = await studio.remove_background(
            image=request.image,
            model=request.model,
        )
        
        return ImageResponse(
            success=result.success,
            image_id=result.image_id,
            image_url=result.image_url,
            image_data=result.image_data,
            mime_type=result.mime_type,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Background removal failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/change-background", response_model=ImageResponse)
async def change_background(
    request: ChangeBackgroundRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Replace the background of an image
    
    Keep the subject and place it in a new scene described by prompt.
    """
    studio = get_image_studio()
    
    try:
        result = await studio.change_background(
            image=request.image,
            new_background=request.new_background,
            model=request.model,
            blend_edges=request.blend_edges,
        )
        
        return ImageResponse(
            success=result.success,
            image_id=result.image_id,
            image_url=result.image_url,
            image_data=result.image_data,
            mime_type=result.mime_type,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Background change failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Video Studio Endpoints ==============

@router.post("/video/generate", response_model=VideoResponse)
async def generate_video(
    request: TextToVideoRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate a video from a text prompt
    
    Similar to Google Video FX
    """
    studio = get_video_studio()
    
    try:
        result = await studio.text_to_video(
            prompt=request.prompt,
            model=request.model,
            duration=request.duration,
            style=request.style,
            aspect_ratio=request.aspect_ratio,
        )
        
        return VideoResponse(
            success=result.success,
            video_id=result.video_id,
            video_url=result.video_url,
            video_data=result.video_data,
            mime_type=result.mime_type,
            duration=result.duration,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/from-image", response_model=VideoResponse)
async def video_from_images(
    request: ImagesToVideoRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate a video from one or more images
    
    Upload images and they will be animated into a video.
    Similar to Google Flow's image-to-video feature.
    """
    studio = get_video_studio()
    
    try:
        result = await studio.images_to_video(
            images=request.images,
            prompt=request.prompt,
            model=request.model,
            duration=request.duration,
            transition_style=request.transition_style,
        )
        
        return VideoResponse(
            success=result.success,
            video_id=result.video_id,
            video_url=result.video_url,
            video_data=result.video_data,
            mime_type=result.mime_type,
            duration=result.duration,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Images to video failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/extend", response_model=VideoResponse)
async def extend_video(
    request: VideoExtendRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Extend an existing video (Flow-like feature)
    
    Upload a video and it will be extended seamlessly.
    The system automatically extracts the last frame and
    generates a natural continuation.
    """
    studio = get_video_studio()
    
    try:
        result = await studio.extend_video(
            video=request.video,
            extension_duration=request.extension_duration,
            prompt=request.prompt,
            model=request.model,
        )
        
        return VideoResponse(
            success=result.success,
            video_url=result.extended_video_url,
            video_data=result.extended_video_data,
            duration=result.total_duration,
            error=result.error,
            metadata={
                "extension_duration": result.extension_duration,
                "original_video": result.original_video_url,
            },
        )
    except Exception as e:
        logger.error(f"Video extend failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/extend-advanced", response_model=VideoResponse)
async def extend_video_advanced(
    request: VideoExtendAdvancedRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Advanced video extension with more options
    
    Features:
    - auto_detect_end_frame: Extract last frame for better continuation
    - concatenate: Combine original + extension into single video (requires FFmpeg)
    """
    studio = get_video_studio()
    
    try:
        result = await studio.extend_video(
            video=request.video,
            extension_duration=request.extension_duration,
            prompt=request.prompt,
            model=request.model,
            auto_detect_end_frame=request.auto_detect_end_frame,
            concatenate=request.concatenate,
        )
        
        return VideoResponse(
            success=result.success,
            video_url=result.extended_video_url,
            video_data=result.extended_video_data,
            duration=result.total_duration,
            error=result.error,
            metadata={
                "extension_duration": result.extension_duration,
                "original_video": result.original_video_url,
                "concatenated": request.concatenate,
                "last_frame_used": result.last_frame_used is not None,
            },
        )
    except Exception as e:
        logger.error(f"Advanced video extend failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/interpolate", response_model=VideoResponse)
async def interpolate_frames(
    request: FrameInterpolateRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate a video that transitions between two frames
    
    Provide a start frame and an end frame, and the system
    will generate a smooth video transition between them.
    Similar to Google Flow's start-to-end frame feature.
    """
    studio = get_video_studio()
    
    try:
        result = await studio.interpolate_frames(
            start_frame=request.start_frame,
            end_frame=request.end_frame,
            duration=request.duration,
            prompt=request.prompt,
            model=request.model,
            interpolation_style=request.interpolation_style,
        )
        
        return VideoResponse(
            success=result.success,
            video_id=result.video_id,
            video_url=result.video_url,
            video_data=result.video_data,
            mime_type=result.mime_type,
            duration=result.duration,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Frame interpolation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== File Serving ==============

@router.get("/image/{filename}")
async def serve_image(filename: str):
    """Serve a generated image file"""
    filepath = Config.IMAGE_SAVE_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath)


@router.get("/video/{filename}")
async def serve_video(filename: str):
    """Serve a generated video file"""
    filepath = Config.VIDEO_SAVE_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(filepath)
