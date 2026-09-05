# Clean Video Workspace - Developer Guide

## 1. Introduction
This guide is for developers maintaining or extending the Clean Video Workspace.

## 2. Architecture Principles
- **Local-First Processing**: All heavy lifting (FFmpeg, React compilation) happens locally. Do not offload to external APIs unless it's a specific MCP service.
- **No Hallucinations**: Scripts must handle missing files and errors gracefully. If an API fails, a local fallback script (e.g., Playwright) should be used.
- **Strict Gating**: The `pipeline_guard.py` enforces the order of operations. Do not write code that circumvents these gates.

## 3. Extending the System

### 3.1 Adding a New Script
1. Place the script in `.agents/plugins/super-video-maker-plugin/scripts/`.
2. Ensure it uses the `UnifiedLogger`:
   ```python
   from utils.logger import UnifiedLogger
   logger = UnifiedLogger("my_script")
   ```
3. Ensure it reads from the centralized configuration:
   ```python
   from utils.config import Config
   config = Config()
   ```
4. Implement standard argparse with a `--help` flag.
5. Add unit tests in `scripts/tests/`.

### 3.2 Adding a New Gate
1. Add the gate logic in a new `_gate.py` file.
2. Register the gate in `pipeline_guard.py`.

### 3.3 Adding a New Template
1. Create the React component in `templates/`.
2. Register it in `TEMPLATE_INDEX.md` and `template_intelligence_matrix.json`.

## 4. Debugging
- Check `.agents/error_log.json` for detailed traces.
- Run `python .agents/launcher.py <script> --debug` (if supported).
- Use `test_utils.py` to verify core utilities.
