# Super Video Maker Plugin

> Commercial motion director for agentic video production.
> An Antigravity Agent Plugin that routes between 7 MCP servers, 19 Python tools,
> 81 Remotion templates, 64 cinematic engine components, and 17 production recipes.

## What It Does

This plugin transforms video ideas into polished, production-ready videos using:

- **81 Remotion Templates**: Cinematic titles, transitions, data visualizations, 
  and VFX overlays
- **7 MCP Servers**: Audio processing, media sourcing, video editing, image 
  manipulation, caching, FFmpeg, and video editing
- **19 Python Tools**: HeyGen avatars, Seedance b-roll, ElevenLabs voice, 
  quality gates, and more
- **17 Production Recipes**: UGC ads, SaaS explainers, talking-head videos, 
  motion graphics, and more

## Requirements

- Node.js 18+
- Python 3.10+
- uv (Python package manager)
- FFmpeg
- ImageMagick (optional, for badge generation)

## Environment Variables

Copy `.env.example` to `.env` and fill in the keys you need:

| Variable | Required For |
|----------|-------------|
| HEYGEN_API_KEY | Avatar generation |
| HEYGEN_AVATAR_ID | Avatar selection |
| HEYGEN_VOICE_ID | Avatar voice |
| FALAI_API_KEY | Seedance video generation |
| OPENAI_API_KEY | Image generation, Whisper |
| ELEVENLABS_API_KEY | Voice generation, music |
| GROQ_API_KEY | Fast transcription |
| REPLICATE_API_TOKEN | Legacy video fallback |
| AWS_* | S3 upload (optional) |

## Installation

### As an Antigravity Plugin (workspace-level)
```bash
cp -r super-video-maker-plugin <workspace>/.agents/plugins/
```

### As an Antigravity Plugin (global)
```bash
cp -r super-video-maker-plugin ~/.gemini/config/plugins/
```

## Setup

```bash
cd super-video-maker-plugin

# Install Remotion dependencies
cd remotion-app && npm install && cd ..

# Install Python dependencies
pip install -r requirements.txt

# Install MCP server dependencies
cd tools/mcp-servers/audio-tools-mcp && uv sync && cd ../../..
cd tools/mcp-servers/media-sources-mcp && uv sync && cd ../../..
cd tools/mcp-servers/video-tools-mcp && uv sync && cd ../../..
cd tools/mcp-servers/image-tools-mcp && uv sync && cd ../../..
cd tools/mcp-servers/common-tools-mcp && uv sync && cd ../../..
cd tools/mcp-servers/Video_Editor_MCP && uv sync && cd ../../..
cd tools/mcp-servers/ffmpeg-mcp-server && npm install && cd ../../..

# Sync templates to Remotion
python scripts/sync_templates.py

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

## Quick Start

### Generate a video
```bash
python tools/video_recipes.py match --goal "make a SaaS product explainer"
python tools/video_recipes.py plan --recipe living-canvas-explainer --goal "SaaS explainer"
```

### Preview in Remotion Studio
```bash
cd remotion-app
npm run studio
```

### Render a video
```bash
cd remotion-app
npx remotion render src/index.ts DynamicRenderer out/video.mp4 \
  --props='{"templateId": "cinematic-title-intro", "durationInFrames": 150}'
```

## Plugin Structure

```
super-video-maker-plugin/
├── plugin.json              # Plugin manifest
├── mcp.json                 # MCP server definitions (7 servers)
├── .env.example             # Environment template
├── README.md                # This file
├── package.json             # Root JS orchestration
├── requirements.txt         # Python dependencies
├── skills/
│   └── super-video-maker/
│       └── SKILL.md         # Main skill instructions
├── templates/               # 81 Remotion templates (source of truth)
├── cinematic-engine/        # 64 cinematic components
├── recipes/                 # 17 production recipes
├── tools/                   # 19 Python tools
│   └── mcp-servers/         # 7 MCP servers
├── references/              # Deep reference docs & playbooks
├── remotion-app/       # Remotion project (build target)
├── hyperframes-template/    # HyperFrames alternative
├── workflows/               # Production workflow scripts
├── commands/                # Quick command templates
├── scripts/                 # Verification & build scripts
└── tests/                   # Unit tests
```

## MCP Servers

| Server | Purpose |
|--------|---------|
| audio-tools-mcp | Voice analysis, timing, normalization |
| media-sources-mcp | Stock media search (Pexels, Pixabay, Freesound, Iconify) |
| video-tools-mcp | Video trimming, resizing, black frame detection |
| image-tools-mcp | Image upscaling, cropping, auto-crop |
| common-tools-mcp | Asset caching (check/save) |
| ffmpeg-mcp-server | Background FFmpeg jobs, concatenation |
| Video_Editor_MCP | Free-form FFmpeg command execution |

## Recipes

Run `python tools/video_recipes.py list` to see all 17 available recipes.

Key recipes:
- `living-canvas-explainer` — Boutique SaaS launch videos
- `ugc-ai-ad` — AI-generated UGC creator ads
- `avatar-explainer` — Proof-driven avatar explainers
- `faceless-broll-ad` — Hook-driven faceless ads
- `motion-collage-explainer` — Artistic concept explainers
- `tabletop-levels-explainer` — Tiered concept builders

## License

MIT

## Credits

Originally built by the Distribb team. Converted to Antigravity Agent Plugin format.
