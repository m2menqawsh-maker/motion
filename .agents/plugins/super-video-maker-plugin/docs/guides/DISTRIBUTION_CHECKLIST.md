# Distribution Checklist

Before publishing to GitHub:

- [ ] Update `plugin.json` author info (name, url)
- [ ] Update `plugin.json` homepage URL
- [ ] Update `plugin.json` repository URL
- [ ] Verify `.env.example` has all needed variables documented
- [ ] Verify `.gitignore` excludes secrets and build artifacts
- [ ] Run `npm run lint` in remotion-app (should be 0 errors)
- [ ] Run `python tools/video_recipes.py validate` (should pass)
- [ ] Run `python scripts/sync_templates.py` (should sync 81 templates)
- [ ] Test MCP server imports (all 7 should import cleanly)
- [ ] Remove any personal API keys or sensitive data
- [ ] Verify no absolute paths remain (grep for C:/ or /Users/)
- [ ] Create GitHub repository
- [ ] Push to GitHub
- [ ] Add repository description and topics
- [ ] Create a release tag v1.0.0

## GitHub Repository Settings

- Name: `super-video-maker-plugin`
- Description: "Commercial motion director for agentic video production. 
  Antigravity Agent Plugin with 81 Remotion templates, 7 MCP servers, 
  17 production recipes."
- Topics: `remotion`, `video-production`, `ai-video`, `agent-plugin`, 
  `antigravity`, `mcp`, `motion-graphics`, `ffmpeg`
- License: MIT
- Visibility: Public (or Private if preferred)
