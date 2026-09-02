# Usage Guide

## Quick Start

### Generate a video

```bash
# Match a recipe to your goal
python tools/video_recipes.py match --goal "make a SaaS product explainer"

# Plan the video
python tools/video_recipes.py plan --recipe living-canvas-explainer --goal "SaaS explainer"
```

### Preview in Remotion Studio

```bash
cd remotion-app
npm run studio
```

Open http://localhost:3000 in your browser.

### Render a video

```bash
cd remotion-app
npx remotion render src/index.ts DynamicRenderer out/video.mp4 \
  --props='{"templateId": "cinematic-title-intro", "durationInFrames": 150}'
```

## Using MCP Servers

### Audio tools

```python
# Analyze voiceover
{
  "ServerName": "audio-tools-mcp",
  "ToolName": "analyze_voiceover",
  "Arguments": {
    "audio_path": "path/to/voiceover.mp3",
    "language": "en"
  }
}

# Normalize loudness
{
  "ServerName": "audio-tools-mcp",
  "ToolName": "normalize_loudness",
  "Arguments": {
    "file_path": "path/to/audio.mp3",
    "target_lufs": -16.0
  }
}
```

### Media sources

```python
# Search for videos
{
  "ServerName": "media-sources-mcp",
  "ToolName": "pexels_search_videos",
  "Arguments": {
    "query": "developer coding modern office",
    "per_page": 5
  }
}

# Download icon
{
  "ServerName": "media-sources-mcp",
  "ToolName": "download_iconify_icon",
  "Arguments": {
    "prefix": "lucide",
    "name": "rocket",
    "color": "#3B82F6",
    "width": 64,
    "height": 64,
    "output_path": "path/to/icon.svg"
  }
}
```

## Production Recipes

### List all recipes

```bash
python tools/video_recipes.py list
```

### Show recipe details

```bash
python tools/video_recipes.py show living-canvas-explainer
```

### Match recipe to goal

```bash
python tools/video_recipes.py match --goal "make a UGC ad for my product"
```

### Plan a video

```bash
python tools/video_recipes.py plan --recipe ugc-ai-ad --goal "Product launch ad"
```

## Quality Gates

### FFmpeg QC

```bash
python tools/ffmpeg_qc.py output/video.mp4
```

### B-roll layout QC

```bash
python tools/broll_layout_qc.py assets/broll/*.mp4 --job-dir ./job
```

### Ad quality gate

```bash
python tools/ad_quality_gate.py final/ad.mp4
```

## Templates

### List templates

```bash
python tools/video_recipes.py templates
```

### Use a template

In your Remotion composition:

```tsx
import { CinematicTitleIntro } from './templates/cinematic-title-intro';

<CinematicTitleIntro
  title="My Video Title"
  subtitle="Subtitle text"
/>
```

## Cinematic Engine

### Camera rig

```tsx
import { CameraRig } from './cinematic-engine/engine/camera/CameraRig';

<CameraRig
  keyframes={[
    { frame: 0, x: 0, y: 0, scale: 1 },
    { frame: 60, x: 100, y: 50, scale: 1.2 },
  ]}
>
  {/* content */}
</CameraRig>
```

### Cursor

```tsx
import { Cursor } from './cinematic-engine/engine/cursor/Cursor';

<Cursor
  keyframes={[
    { frame: 0, x: 100, y: 100 },
    { frame: 30, x: 200, y: 150, click: true },
  ]}
/>
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| HEYGEN_API_KEY | Yes | HeyGen avatar generation |
| HEYGEN_AVATAR_ID | Yes | Default avatar ID |
| HEYGEN_VOICE_ID | Yes | Default voice ID |
| FALAI_API_KEY | Yes | Seedance video generation |
| OPENAI_API_KEY | Yes | Image generation, Whisper |
| ELEVENLABS_API_KEY | Yes | Voice generation, music |
| GROQ_API_KEY | Yes | Fast transcription |
| REPLICATE_API_TOKEN | No | Legacy video fallback |
| AWS_ACCESS_KEY_ID | No | S3 upload |
| AWS_SECRET_ACCESS_KEY | No | S3 upload |
| AWS_REGION | No | S3 region |
| AWS_S3_BUCKET | No | S3 bucket name |
