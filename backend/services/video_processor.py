"""
Gemini Ultra Gateway - Video Processor
Video frame extraction, concatenation, and processing utilities
Supports FFmpeg (if available) or pure Python fallback
"""

import os
import io
import base64
import logging
import tempfile
import subprocess
import shutil
from typing import Optional, List, Tuple, Union
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger("gemini.video_processor")


@dataclass
class FrameInfo:
    """Information about an extracted frame"""
    frame_number: int
    timestamp: float
    data: bytes
    mime_type: str = "image/jpeg"
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass 
class VideoInfo:
    """Video metadata"""
    duration: float
    width: int
    height: int
    fps: float
    frame_count: int
    codec: str
    format: str


class VideoProcessor:
    """
    Video processing utilities for frame extraction and manipulation
    
    Features:
    - Extract frames from video (first, last, specific timestamps)
    - Get video metadata (duration, resolution, fps)
    - Concatenate videos (for extend feature)
    - Generate thumbnails
    """
    
    def __init__(self):
        self._ffmpeg_path = self._find_ffmpeg()
        self._ffprobe_path = self._find_ffprobe()
        self._has_ffmpeg = self._ffmpeg_path is not None
        
        if self._has_ffmpeg:
            logger.info(f"FFmpeg found: {self._ffmpeg_path}")
        else:
            logger.warning("FFmpeg not found - using limited pure Python processing")
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable"""
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        
        # Check common locations on Windows
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"D:\ffmpeg\bin\ffmpeg.exe",
        ]
        
        for path in common_paths:
            if os.path.isfile(path):
                return path
        
        return None
    
    def _find_ffprobe(self) -> Optional[str]:
        """Find FFprobe executable"""
        ffprobe_path = shutil.which("ffprobe")
        if ffprobe_path:
            return ffprobe_path
        
        # Check common locations on Windows
        common_paths = [
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
            r"D:\ffmpeg\bin\ffprobe.exe",
        ]
        
        for path in common_paths:
            if os.path.isfile(path):
                return path
        
        return None
    
    @property
    def has_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        return self._has_ffmpeg
    
    def get_video_info(self, video_path: Union[str, Path]) -> Optional[VideoInfo]:
        """
        Get video metadata using FFprobe
        
        Args:
            video_path: Path to video file
            
        Returns:
            VideoInfo object or None if failed
        """
        if not self._ffprobe_path:
            logger.warning("FFprobe not available")
            return None
        
        try:
            cmd = [
                self._ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"FFprobe failed: {result.stderr}")
                return None
            
            import json
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            if not video_stream:
                return None
            
            format_info = data.get("format", {})
            
            # Parse frame rate (can be "30/1" or "29.97")
            fps_str = video_stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den)
            else:
                fps = float(fps_str)
            
            return VideoInfo(
                duration=float(format_info.get("duration", 0)),
                width=int(video_stream.get("width", 0)),
                height=int(video_stream.get("height", 0)),
                fps=fps,
                frame_count=int(video_stream.get("nb_frames", 0)),
                codec=video_stream.get("codec_name", "unknown"),
                format=format_info.get("format_name", "unknown"),
            )
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None
    
    def extract_frame(
        self,
        video_path: Union[str, Path],
        timestamp: float = 0.0,
        output_format: str = "jpeg",
        quality: int = 2,
    ) -> Optional[FrameInfo]:
        """
        Extract a single frame at specific timestamp
        
        Args:
            video_path: Path to video file
            timestamp: Time in seconds
            output_format: Output image format (jpeg, png)
            quality: Quality for JPEG (2-31, lower is better)
            
        Returns:
            FrameInfo with frame data or None
        """
        if not self._ffmpeg_path:
            return self._extract_frame_python(video_path, timestamp)
        
        try:
            with tempfile.NamedTemporaryFile(
                suffix=f".{output_format}",
                delete=False
            ) as tmp:
                tmp_path = tmp.name
            
            cmd = [
                self._ffmpeg_path,
                "-ss", str(timestamp),
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", str(quality),
                "-y",
                tmp_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Frame extraction failed: {result.stderr.decode()}")
                return None
            
            with open(tmp_path, "rb") as f:
                frame_data = f.read()
            
            os.unlink(tmp_path)
            
            mime_type = "image/jpeg" if output_format == "jpeg" else "image/png"
            
            return FrameInfo(
                frame_number=int(timestamp * 30),  # Approximate
                timestamp=timestamp,
                data=frame_data,
                mime_type=mime_type,
            )
            
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return None
    
    def extract_first_frame(
        self,
        video_path: Union[str, Path],
    ) -> Optional[FrameInfo]:
        """Extract the first frame of a video"""
        return self.extract_frame(video_path, timestamp=0.0)
    
    def extract_last_frame(
        self,
        video_path: Union[str, Path],
    ) -> Optional[FrameInfo]:
        """
        Extract the last frame of a video
        This is useful for video extension (Flow-like feature)
        """
        info = self.get_video_info(video_path)
        
        if info and info.duration > 0:
            # Get frame 0.1 seconds before the end
            timestamp = max(0, info.duration - 0.1)
            return self.extract_frame(video_path, timestamp=timestamp)
        
        # Fallback: try getting a late frame
        return self.extract_frame(video_path, timestamp=10.0)
    
    def extract_frames_at_intervals(
        self,
        video_path: Union[str, Path],
        interval: float = 1.0,
        max_frames: int = 10,
    ) -> List[FrameInfo]:
        """
        Extract frames at regular intervals
        
        Args:
            video_path: Path to video file
            interval: Time between frames in seconds
            max_frames: Maximum number of frames to extract
            
        Returns:
            List of FrameInfo objects
        """
        frames = []
        info = self.get_video_info(video_path)
        
        if not info:
            return frames
        
        current_time = 0.0
        while current_time < info.duration and len(frames) < max_frames:
            frame = self.extract_frame(video_path, timestamp=current_time)
            if frame:
                frames.append(frame)
            current_time += interval
        
        return frames
    
    def concatenate_videos(
        self,
        video_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
        crossfade_duration: float = 0.0,
    ) -> bool:
        """
        Concatenate multiple videos into one
        
        Args:
            video_paths: List of video file paths
            output_path: Output video path
            crossfade_duration: Duration of crossfade between videos (0 for hard cut)
            
        Returns:
            True if successful
        """
        if not self._ffmpeg_path:
            logger.error("FFmpeg required for video concatenation")
            return False
        
        if len(video_paths) < 2:
            logger.error("Need at least 2 videos to concatenate")
            return False
        
        try:
            if crossfade_duration > 0:
                return self._concat_with_crossfade(
                    video_paths, output_path, crossfade_duration
                )
            else:
                return self._concat_simple(video_paths, output_path)
                
        except Exception as e:
            logger.error(f"Video concatenation failed: {e}")
            return False
    
    def _concat_simple(
        self,
        video_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
    ) -> bool:
        """Simple concatenation without transition"""
        # Create concat list file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False
        ) as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")
            list_path = f.name
        
        try:
            cmd = [
                self._ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"Concatenation failed: {result.stderr.decode()}")
                return False
            
            return True
            
        finally:
            os.unlink(list_path)
    
    def _concat_with_crossfade(
        self,
        video_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
        crossfade_duration: float,
    ) -> bool:
        """Concatenation with crossfade transitions"""
        # Build complex filter for crossfade
        # This is more complex and requires re-encoding
        
        inputs = []
        for path in video_paths:
            inputs.extend(["-i", str(path)])
        
        # Build filter complex
        filter_parts = []
        n = len(video_paths)
        
        for i in range(n - 1):
            if i == 0:
                filter_parts.append(
                    f"[{i}:v][{i+1}:v]xfade=transition=fade:"
                    f"duration={crossfade_duration}:"
                    f"offset=0[v{i}]"
                )
            else:
                filter_parts.append(
                    f"[v{i-1}][{i+1}:v]xfade=transition=fade:"
                    f"duration={crossfade_duration}:"
                    f"offset=0[v{i}]"
                )
        
        filter_complex = ";".join(filter_parts)
        output_stream = f"[v{n-2}]" if n > 2 else "[v0]"
        
        cmd = [
            self._ffmpeg_path,
            *inputs,
            "-filter_complex", filter_complex,
            "-map", output_stream,
            "-y",
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=600
        )
        
        if result.returncode != 0:
            logger.error(f"Crossfade concat failed: {result.stderr.decode()}")
            return False
        
        return True
    
    def generate_thumbnail(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        width: int = 320,
        timestamp: float = 1.0,
    ) -> bool:
        """
        Generate a thumbnail from video
        
        Args:
            video_path: Source video path
            output_path: Output thumbnail path
            width: Thumbnail width (height auto-calculated)
            timestamp: Time to extract thumbnail from
            
        Returns:
            True if successful
        """
        if not self._ffmpeg_path:
            logger.error("FFmpeg required for thumbnail generation")
            return False
        
        try:
            cmd = [
                self._ffmpeg_path,
                "-ss", str(timestamp),
                "-i", str(video_path),
                "-vframes", "1",
                "-vf", f"scale={width}:-1",
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return False
    
    def _extract_frame_python(
        self,
        video_path: Union[str, Path],
        timestamp: float,
    ) -> Optional[FrameInfo]:
        """
        Pure Python frame extraction fallback (limited functionality)
        Uses imageio if available
        """
        try:
            import imageio.v3 as iio
            
            frames = iio.imread(str(video_path), index=int(timestamp * 30))
            
            # Convert numpy array to JPEG bytes
            from PIL import Image
            img = Image.fromarray(frames)
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            frame_data = buffer.getvalue()
            
            return FrameInfo(
                frame_number=int(timestamp * 30),
                timestamp=timestamp,
                data=frame_data,
                mime_type="image/jpeg",
            )
            
        except ImportError:
            logger.error("imageio not installed - cannot extract frames without FFmpeg")
            return None
        except Exception as e:
            logger.error(f"Python frame extraction failed: {e}")
            return None
    
    def video_to_base64(self, video_path: Union[str, Path]) -> str:
        """Convert video file to base64 string"""
        with open(video_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    
    def base64_to_video(
        self,
        b64_data: str,
        output_path: Union[str, Path],
    ) -> bool:
        """Save base64 video data to file"""
        try:
            video_bytes = base64.b64decode(b64_data)
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            return True
        except Exception as e:
            logger.error(f"Failed to save video: {e}")
            return False
    
    def frame_to_base64(self, frame: FrameInfo) -> str:
        """Convert frame data to base64 string"""
        return base64.b64encode(frame.data).decode()


# Global processor instance
_processor: Optional[VideoProcessor] = None


def get_video_processor() -> VideoProcessor:
    """Get or create the global video processor instance"""
    global _processor
    if _processor is None:
        _processor = VideoProcessor()
    return _processor
