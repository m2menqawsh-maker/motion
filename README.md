# Clean Video Workspace (Motion Production Engine)

> Developed by **Momen (m2menqawsh-maker)**.
> Commercial motion director for agentic video production.
> An enterprise-grade pipeline that routes between MCP servers, unified Remotion templates, and production recipes.

## What It Does

This system transforms video ideas into polished, production-ready videos relying on a unified 9-stage pipeline:

- **Remotion Templates**: Cinematic titles, transitions, data visualizations, and VFX overlays in `templates/`
- **Agent Subsystems (Plugins)**: Antigravity MCP servers for audio processing, media sourcing, video tools, image tools, and common tools (located in `.agents/plugins/`).
- **Active Core Tools**: `media_pipeline.py`, `image_provider.py`, `elevenlabs_voice.py`, `heygen_client.py`.
- **Active Recipes**: Guided generation via recipes and blueprints in `ground-truth/`.

## Requirements

- Node.js 18+
- Python 3.10+
- uv (Python package manager)
- FFmpeg

## Environment Variables

Copy `.env.example` to `.env` and fill in the keys you need for both the Core Engine and the Agent Tools. All configuration is centralized at the root.

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

## Workspace Structure

```
clean-video-workspace/
├── .agents/                 # AI Agent Plugins and MCP Servers
├── api/                     # Core FastAPI Backend services
├── contracts/               # Pydantic schemas and pipeline constraints
├── documentation/           # System architecture and guides
├── ground-truth/            # Catalogs, indexes, and golden records
├── projects/                # Generated video projects output
├── recipes/                 # Reusable orchestration playbooks
├── registry/                # Centralized template registry
├── remotion-app/            # The physical React/Remotion renderer
├── scripts/                 # Core Python engine and pipeline scripts
├── templates/               # React TSX visual templates and effects
└── tests/                   # 160+ Fortress CI tests (Architecture, Security, etc.)
```

## Architecture & Integration

This project uses a unified pipeline (`scripts/pipeline.py`) that strictly separates concerns:
- Canonical templates, scripts, recipes, references, security configs, and ground truth are owned by the **Repository Root**.
- The Antigravity Agents operate through the `.agents/` plugin system to provide IDE discovery, skills, MCP servers, and tool adapters.
- See root documentation: `documentation/README.md` and `documentation/architecture/ARCHITECTURE_TRUTH.md`.

## License

MIT License - Copyright (c) 2026 Momen (m2menqawsh-maker)
