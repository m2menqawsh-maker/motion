# Installation Guide

## Prerequisites

Before installing, ensure you have:

- **Node.js 18+**: `node --version`
- **Python 3.10+**: `python --version`
- **uv**: `uv --version` (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **FFmpeg**: `ffmpeg -version`
- **ImageMagick** (optional): `magick --version`

## Installation Steps

### 1. Clone the repository

```bash
git clone https://github.com/m2menqawsh-maker/super-video-maker-plugin.git
cd super-video-maker-plugin
```

### 2. Install Remotion dependencies

```bash
cd remotion-app
npm install
cd ..
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install MCP server dependencies

```bash
# Audio tools
cd tools/mcp-servers/audio-tools-mcp
uv sync
cd ../../..

# Media sources
cd tools/mcp-servers/media-sources-mcp
uv sync
cd ../../..

# Video tools
cd tools/mcp-servers/video-tools-mcp
uv sync
cd ../../..

# Image tools
cd tools/mcp-servers/image-tools-mcp
uv sync
cd ../../..

# Common tools
cd tools/mcp-servers/common-tools-mcp
uv sync
cd ../../..

# Video Editor
cd tools/mcp-servers/Video_Editor_MCP
uv sync
cd ../../..

# FFmpeg server
cd tools/mcp-servers/ffmpeg-mcp-server
npm install
cd ../../..
```

### 5. Sync templates

```bash
python scripts/sync_templates.py
```

### 6. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 7. Verify installation

```bash
# Test Remotion
cd remotion-app
npm run studio

# Test MCP servers
cd tools/mcp-servers/audio-tools-mcp
python -c "import server; print('✅ audio-tools-mcp OK')"
```

## Antigravity Integration

### Option A: Workspace-level installation

```bash
cp -r super-video-maker-plugin <workspace>/.agents/plugins/
```

### Option B: Global installation

```bash
cp -r super-video-maker-plugin ~/.gemini/config/plugins/
```

## Troubleshooting

### Remotion won't start

```bash
cd remotion-app
rm -rf node_modules package-lock.json
npm install
```

### MCP server won't import

```bash
cd tools/mcp-servers/<server-name>
uv sync
python -c "import server; print('OK')"
```

### Templates not syncing

```bash
python scripts/sync_templates.py
```
