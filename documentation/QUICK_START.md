# Clean Video Workspace - Quick Start

## 1. Prerequisites
- Node.js (v18+)
- Python 3.10+
- FFmpeg installed and in PATH
- MCP servers configured and running

## 2. Starting a New Project
To start a new video project, simply tell the AI Agent:
> "Start a new video project about [Topic]. Here is the voiceover file: [Path/URL]"

## 3. What the Agent Will Do:
1. Initialize the project folder.
2. Analyze the voiceover (if provided).
3. Generate a step-by-step plan.
4. Wait for your approval.
5. Fetch assets and build the video.
6. Open the Studio for your review.

## 4. Manual Approvals Required
- **Plan Approval**: Review `01_plan.md` and say "Approved".
- **Studio Approval**: After previewing the video, create a file named `.studio_approved` in the project root to unlock the final render.

Happy Video Making!
