# Architecture

## Overview

Super Video Maker Plugin is a modular video production system built on:

- **Remotion**: React-based video rendering
- **MCP (Model Context Protocol)**: Tool integration
- **Agent Plugins Spec v1.0.0**: Plugin packaging standard

## Plugin Structure

```
super-video-maker-plugin/
├── plugin.json              # Plugin manifest (Agent Plugins Spec)
├── mcp.json                 # MCP server definitions
├── skills/                  # Agent skills
│   └── super-video-maker/
│       └── SKILL.md         # Main skill instructions
├── templates/               # 81 Remotion templates
├── cinematic-engine/        # 64 cinematic components
├── recipes/                 # 17 production recipes
├── tools/                   # 19 Python tools
│   └── mcp-servers/         # 7 MCP servers
├── references/              # Documentation & playbooks
├── remotion-template/       # Remotion build target
└── workflows/               # Production workflows
```

## MCP Servers

| Server | Language | Purpose |
|--------|----------|---------|
| audio-tools-mcp | Python | Voice analysis, timing, normalization |
| media-sources-mcp | Python | Stock media search & download |
| video-tools-mcp | Python | Video trimming, resizing |
| image-tools-mcp | Python | Image upscaling, cropping |
| common-tools-mcp | Python | Asset caching |
| ffmpeg-mcp-server | Node.js | FFmpeg jobs, concatenation |
| Video_Editor_MCP | Python | Free-form FFmpeg commands |

## Templates

81 templates organized into 7 categories:

| Category | Count | Examples |
|----------|-------|----------|
| Typography & Captions | 14 | animated-text, cinematic-title-intro |
| Transitions | 11 | cross-dissolve, whip-pan |
| Data & Stats | 10 | stat-counter, line-chart |
| Containers & Cards | 13 | card-flip, picture-in-picture |
| Branding & Logos | 11 | logo-fade-reveal, lower-third |
| CTA & Engagement | 6 | countdown-timer, end-card |
| VFX & Overlays | 15 | noise-grain, film-burn |

## Cinematic Engine

64 components for SaaS product demos:

- **Camera**: CameraRig, AutoZoom
- **Cursor**: Cursor, CursorSprite
- **Layout**: LayoutContext, LayoutWindow
- **Audio**: AudioManager
- **Primitives**: Headline, CountUp, Window
- **Scenes**: ChaosDesktop, FeatureShowcase, ProductReveal

## Production Pipeline

```
Intake → Script → Assets → Assembly → QC → Export
```

1. **Intake**: Gather requirements, match recipe
2. **Script**: Write VO, plan visuals
3. **Assets**: Fetch/process media via MCP
4. **Assembly**: Build Remotion composition
5. **QC**: Run quality gates
6. **Export**: Render final video

## Key Technologies

- **Remotion 4.x**: React-based video rendering
- **TypeScript**: Type-safe compositions
- **Python 3.10+**: Tool scripting
- **FFmpeg**: Video processing
- **ElevenLabs**: Voice generation
- **HeyGen**: Avatar generation
- **Seedance**: B-roll generation
- **Pexels/Pixabay**: Stock media
