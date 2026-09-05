# Clean Video Workspace - User Guide

## 1. Introduction
Welcome to the Clean Video Workspace. This guide will help you create automated videos without writing complex code. You act as the "Producer/Client" and the AI agent acts as the "Master Planner & Pipeline Orchestrator".

## 2. Project Lifecycle
Every video project goes through these stages:

1. **Initialization**: Create a new project folder under `projects/`.
2. **Briefing**: Provide the agent with your vision, script, and assets (or ask it to fetch them).
3. **Planning**: The agent will create a detailed `01_plan.md`. **You must review and approve this plan.**
4. **Asset Gathering**: The agent uses MCPs to download required stock footage and audio.
5. **Blueprint & Building**: The agent generates React/Remotion code.
6. **Review (Studio)**: You will be asked to review the video in the Remotion Studio. You must manually create a `.studio_approved` file to proceed.
7. **Final Render**: The video is rendered and ready for delivery.

## 3. Important Rules for Users
- **Do not bypass the gates**: The system relies on manual approvals (e.g., plan approval, studio approval). Do not force the agent to skip them.
- **Provide clear feedback**: If a test render looks wrong, ask the agent to fix the specific scene in the plan or blueprint.
- **Use the config**: If you want to change default colors or styles, ask the agent to modify `.agents/config.yaml`.

## 4. Common Commands
While the AI handles the execution, you can monitor the progress by checking:
- `projects/<id>/01_plan.md`
- `projects/<id>/05_blueprint_human.md`
- `FINAL_AUDIT_REPORT.md` (for system health)
