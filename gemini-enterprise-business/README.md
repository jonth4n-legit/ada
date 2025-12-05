# Gemini Ultra Gateway

A comprehensive API gateway for Gemini Business with advanced media generation features, combining the best of Google's Video FX (Flow) and Image FX (Whisk).

<div align="center">
  <h3>One Gateway, All Gemini Features</h3>
  <p>Text | Images | Videos | All in One API</p>
</div>

## Features

### Core Features
- **OpenAI-Compatible API** - Drop-in replacement for OpenAI's chat completions
- **Multi-Account Load Balancing** - Distribute requests across multiple Gemini accounts
- **Session Persistence** - Maintain conversation context across requests
- **Auto Account Recovery** - Automatic failover when accounts hit rate limits

### Image Studio (Like Google Whisk/ImageFX)
- **Text to Image** - Generate images from text prompts
- **Image Editing** - Modify existing images with prompts
- **Style Remix** - Apply style from one image to another
- **Ingredients Generation** - Whisk-like feature combining Subject + Style + Scene

### Video Studio (Like Google Flow/VideoFX)
- **Text to Video** - Generate videos from text prompts
- **Image(s) to Video** - Animate one or more images
- **Video Extension** - Extend videos seamlessly (auto-detect end frame)
- **Frame Interpolation** - Generate video between start and end frames

## Supported Models

| Model | Type | Description |
|-------|------|-------------|
| `gemini-auto` | Auto | Automatic model selection |
| `gemini-2.5-flash` | Text | Fast responses |
| `gemini-2.5-pro` | Text | Balanced performance |
| `gemini-3-pro-preview` | Text | Advanced features |
| `gemini-*-image` | Image | Image generation |
| `gemini-*-video` | Video | Video generation |
| `gemini-*-search` | Search | Web grounding enabled |

## Quick Start

### 1. Clone and Configure

```bash
# Navigate to the project
cd gemini-ultra-gateway

# Copy environment example
cp .env.example .env

# Edit .env with your Gemini Business credentials
```

### 2. Get Gemini Business Credentials

1. Go to [Gemini Business](https://business.gemini.google)
2. Open browser DevTools (F12) → Application → Cookies
3. Copy these values:
   - `__Secure-C_SES` → `ACCOUNT1_SECURE_C_SES`
   - `csesidx` (from URL or network requests) → `ACCOUNT1_CSESIDX`
   - `configId` (from network requests) → `ACCOUNT1_CONFIG_ID`

### 3. Run with Docker

```bash
docker-compose up -d
```

Or run directly:

```bash
cd backend
pip install -r ../requirements.txt
python main.py
```

### 4. Access the API

- **API Docs**: http://localhost:5000/docs
- **Health Check**: http://localhost:5000/v1/health

## API Usage

### OpenAI-Compatible Chat

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="http://localhost:5000/v1"
)

# Text generation
response = client.chat.completions.create(
    model="gemini-3-pro-preview",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Image generation
response = client.chat.completions.create(
    model="gemini-3-pro-preview-image",
    messages=[{"role": "user", "content": "Generate a futuristic city"}]
)
```

### Image Studio API

```python
import requests

# Text to Image
response = requests.post(
    "http://localhost:5000/v1/image/generate",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "prompt": "A beautiful sunset over mountains",
        "style": "photorealistic",
        "aspect_ratio": "16:9"
    }
)

# Whisk-like Ingredients Generation
response = requests.post(
    "http://localhost:5000/v1/image/from-ingredients",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "ingredients": [
            {"type": "subject", "image": "base64_cat_photo..."},
            {"type": "style", "image": "base64_van_gogh..."},
            {"type": "scene", "prompt": "cozy living room"}
        ],
        "prompt": "A cat relaxing",
        "blend_mode": "balanced"
    }
)
```

### Video Studio API

```python
import requests

# Text to Video
response = requests.post(
    "http://localhost:5000/v1/video/generate",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "prompt": "A cat walking in a garden",
        "duration": 5,
        "style": "cinematic"
    }
)

# Video Extension (Flow-like)
response = requests.post(
    "http://localhost:5000/v1/video/extend",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "video": "base64_video_data...",
        "extension_duration": 5,
        "prompt": "Continue the scene naturally"
    }
)

# Frame Interpolation
response = requests.post(
    "http://localhost:5000/v1/video/interpolate",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "start_frame": "base64_start_image...",
        "end_frame": "base64_end_image...",
        "duration": 3,
        "interpolation_style": "smooth"
    }
)
```

## API Endpoints

### OpenAI Compatible
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/models` | List available models |
| POST | `/v1/chat/completions` | Chat completion (streaming supported) |

### Image Studio
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/image/generate` | Text to image |
| POST | `/v1/image/edit` | Edit existing image |
| POST | `/v1/image/remix` | Style transfer |
| POST | `/v1/image/from-ingredients` | Whisk-like generation |

### Video Studio
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/video/generate` | Text to video |
| POST | `/v1/video/from-image` | Image(s) to video |
| POST | `/v1/video/extend` | Extend video (Flow-like) |
| POST | `/v1/video/interpolate` | Frame interpolation |

## Multi-Account Configuration

Add multiple accounts for load balancing:

```env
# Account 1
ACCOUNT1_NAME=primary
ACCOUNT1_SECURE_C_SES=...
ACCOUNT1_CSESIDX=...
ACCOUNT1_CONFIG_ID=...

# Account 2
ACCOUNT2_NAME=backup
ACCOUNT2_SECURE_C_SES=...
ACCOUNT2_CSESIDX=...
ACCOUNT2_CONFIG_ID=...

# Add more as needed...
```

## Project Structure

```
gemini-ultra-gateway/
├── backend/
│   ├── core/               # Core modules
│   │   ├── config.py       # Configuration
│   │   ├── account_pool.py # Multi-account management
│   │   ├── jwt_manager.py  # JWT handling
│   │   └── session_manager.py
│   ├── services/           # Business logic
│   │   ├── chat_handler.py # Chat completions
│   │   ├── image_studio.py # Image generation
│   │   └── video_studio.py # Video generation
│   ├── api/                # API endpoints
│   │   ├── openai_compat.py
│   │   └── media_studio.py
│   └── main.py             # Application entry
├── frontend/               # Admin UI (TODO)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Comparison with Google Labs

| Feature | Google Labs | Gemini Ultra Gateway |
|---------|-------------|---------------------|
| Text Generation | ✅ | ✅ |
| Image Generation | ✅ ImageFX | ✅ Image Studio |
| Video Generation | ✅ VideoFX | ✅ Video Studio |
| Style Mixing | ✅ Whisk | ✅ Ingredients API |
| Video Extension | ✅ Flow | ✅ /video/extend |
| Frame Interpolation | ✅ Flow | ✅ /video/interpolate |
| API Access | ❌ | ✅ |
| Multi-Account | ❌ | ✅ |
| Self-Hosted | ❌ | ✅ |

## Credits

This project combines and enhances features from:
- Gemini-Link-System (Core API, Admin Panel)
- business-gemini-pool (Video generation)
- business-gemini-x (Auto-login, Cookie refresh)
- business2api (Go performance optimizations)
- gemini_business (Gemini API format)

## License

MIT License
