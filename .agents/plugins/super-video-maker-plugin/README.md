# Super Video Maker Plugin

> Commercial motion director for agentic video production.
> An Antigravity Agent Plugin that routes between MCP servers, unified Remotion templates, and production recipes.

## What It Does

This plugin transforms video ideas into polished, production-ready videos relying on the unified pipeline:

- **Remotion Templates**: Cinematic titles, transitions, data visualizations, and VFX overlays in `templates/`
- **MCP Servers**: Audio processing, media sourcing, video tools, image tools, and common tools.
- **Active Tools**: `media_pipeline.py`, `image_provider.py`, `elevenlabs_voice.py`, `heygen_client.py`.
- **Active Recipes**: `avatar-insta-reel.md`.

## Requirements

- Node.js 18+
- Python 3.10+
- uv (Python package manager)
- FFmpeg

## Environment Variables

Copy `.env.example` to `.env` and fill in the keys you need:

| Variable | Required For |
|----------|-------------|
| HEYGEN_API_KEY | Avatar generation |
| FALAI_API_KEY | Seedance video generation |
| OPENAI_API_KEY | Image generation, Whisper |
| ELEVENLABS_API_KEY | Voice generation, music |
| GROQ_API_KEY | Fast transcription |

## Quick Start

### Generate a video
```bash
python scripts/pipeline.py <project_id>
```

## Plugin Structure

```
super-video-maker-plugin/
├── plugin.json              # Plugin manifest
├── mcp.json                 # MCP server definitions
├── .env.example             # Environment template
├── README.md                # This file
├── package.json             # Orchestration
├── requirements.txt         # Python dependencies
├── docs/                    # Central documentation
├── skills/                  # Agent skills
├── templates/               # Remotion templates (source of truth)
├── recipes/                 # Production recipes
├── tools/                   # Python tools & MCP servers
├── commands/                # Quick command templates
└── scripts/                 # Verification & build scripts
```

## Documentation

- **[Usage Guide](docs/guides/USAGE.md)** — Quickstart and detailed operational instructions.
- **[Architecture (v2.0)](docs/guides/ARCHITECTURE.md)** — Core design principles.

## MCP Servers

| Server | Purpose |
|--------|---------|
| audio-tools-mcp | Voice analysis, timing, normalization |
| media-sources-mcp | Stock media search (Pexels, Pixabay, Freesound, Iconify) |
| video-tools-mcp | Video trimming, resizing, black frame detection |
| image-tools-mcp | Image upscaling, cropping, auto-crop |
| common-tools-mcp | Asset caching (check/save) |

## License

MIT
