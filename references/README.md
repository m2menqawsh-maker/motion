> [!NOTE]
> **Source of Truth Hierarchy:**
> This is a Reference Document (Level 5).
> Current Architectural Authority: `ARCHITECTURE_TRUTH.md`
> Agent Instructions Authority: `.agents/AGENTS.md`
> Do not use this document to bypass official pipeline gates or engine boundaries.

# Super Video Maker Skill

**Built by the team at Distribb — the SEO and growth autopilot for operators.**  
**→ Build and scale content systems with us at [distribb.io](https://distribb.io).**

---

> **An end-to-end AI video production skill for agentic coding frameworks.** Give your Cursor, Claude Code, or other shell-capable AI agent a video idea, source link, product flow, screen recording, or script, and this skill teaches the agent how to turn it into a polished video using HeyGen avatars, screen recordings, AI b-roll, OpenAI image generation, Remotion, HyperFrames, FFmpeg, captions, music, and quality-control loops.

This repo is designed to be dropped into an AI agent project as a reusable skill. It includes the actual instruction file (`SKILL.md`), deep production references, workflow examples, FFmpeg recipes, Python tools, and starter Remotion/HyperFrames templates.

The flagship format is:

**Zero-Build Video Engineering** — No React coding required. The agent creates a `05_blueprint.json` and the Master Engine renders it using any of the 169+ pre-registered Remotion components.

---

## What It Can Make

- **Avatar Explainers:** trending-news or tutorial videos with a HeyGen avatar, source receipts, b-roll, captions, and CTA outro.
- **Screen-recorded demos:** product walkthroughs with cursor logs, zooms, click effects, captions, narration, and optional S3 upload.
- **Faceless explainers:** motion graphics, UI cards, screenshots, typographic cards, and generated scenes using the `169+ unified templates`.
- **Repurposed shorts:** long videos clipped, captioned, reformatted, and exported for social platforms.
- **Data-Driven Compositions:** Completely programmatic videos rendered from a `05_blueprint.json` file via the Master Engine without writing a single line of React code.

---

## Why This Skill Exists

Most AI video tools stop at one layer:

- one avatar generator,
- one image generator,
- one screen recorder,
- one captioning tool,
- one FFmpeg command.

Real videos need the whole pipeline:

1. pick the story,
2. write the script,
3. gather source proof,
4. generate or capture the right visuals,
5. sync everything to the actual voiceover,
6. compose the timeline,
7. burn captions,
8. normalize audio,
9. check visual layout,
10. export clean files.

This skill gives an AI agent the operating system for that process.

---

## Repository Structure

```text
super-video-maker-skill/
├── SKILL.md                         # Main agent instructions
├── REFERENCE.md                     # Provider choices, design logic, quality gates
├── WORKFLOW_EXAMPLES.md             # Full recipes, including Avatar Explainers
├── FFMPEG_PLAYBOOK.md               # Practical FFmpeg recipes
├── REMOTION_VIDEO_GUIDE.md          # Remotion production style guide
├── requirements.txt                 # Python dependencies
├── package.json                     # Root JS tooling dependencies
├── .env.example                     # Environment variable template
├── tools/
│   ├── video_recipes.py             # Match, plan, and validate video recipes
│   ├── video_orchestrator.py        # Job lifecycle and state orchestrator
│   ├── elevenlabs_voice.py          # Voiceover generation helper
│   ├── heygen_client.py             # HeyGen avatar generation + polling + download
│   ├── fal_seedance_video.py        # Seedance 2.5 video generation via fal.ai
│   ├── replicate_video.py           # Seedance 2.0 via Replicate (legacy fallback)
│   ├── image_provider.py            # OpenAI image generation/editing helper
│   ├── screen_recorder.py           # FFmpeg/Xvfb or Playwright screen recording
│   ├── agent_browser_recorder.py    # Agent-operated browser proof recording
│   ├── demo_video_composer.py       # Polished product demo composer
│   ├── video_captioner.py           # Whisper + ASS captions + shorts rendering
│   ├── music_provider.py            # ElevenLabs music helper
│   ├── local_explainer_broll.py     # Local fallback b-roll renderer
│   ├── ugc_ad_runner.py             # UGC ad test runner and variant generator
│   ├── media_pipeline.py            # Idempotent media lifecycle and caching
│   ├── broll_layout_qc.py           # Visual layout QC contact sheets
│   ├── ad_quality_gate.py           # Quality gate for video ads
│   └── ffmpeg_qc.py                 # Final technical QC
├── scripts/
│   ├── stage_gate.py                # 9-stage production gate validator
│   ├── validate_blueprint.py        # Blueprint timeline & motion personality validator
│   ├── materialize_project.py       # Single gateway to materialize media into build
│   ├── open_studio.py               # Orchestrator to open the local preview server
│   ├── render_project.py            # Final production MP4 renderer
│   └── audit_skill.py               # Complete skill integrity audit suite
├── remotion-app/               # The Zero-Build Master Engine
└── references/                 # Core documentation and protocol playbooks
```

---

## Install

Clone the repo:

```bash
git clone https://github.com/Bomx/super-video-maker-skill.git
cd super-video-maker-skill
```

Install Python dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

Install JavaScript dependencies for the Master Engine:

```bash
npm install
cd remotion-app && npm install && cd ..
```

Install system dependencies:

```bash
brew install ffmpeg
```

On Linux servers you may also need:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg xvfb
```

Create your environment file:

```bash
cp .env.example .env
```

Then fill in the keys you plan to use.

---

## Environment Variables

Minimum useful setup:

```bash
HEYGEN_API_KEY=
HEYGEN_AVATAR_ID=
HEYGEN_VOICE_ID=
OPENAI_API_KEY=
REPLICATE_API_TOKEN=
ELEVENLABS_API_KEY=
```

Optional:

```bash
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
AWS_S3_BUCKET=
SOUNDTRACKS_S3_BASE_URL=
ANTHROPIC_API_KEY=
```

Provider notes:

- **HeyGen** renders avatar video. `HEYGEN_AVATAR_ID` and `HEYGEN_VOICE_ID` are separate values.
- **OpenAI** is used for image generation/editing and Whisper transcription.
- **fal.ai** runs Seedance 2.5 b-roll. **Replicate** is a legacy Seedance 2.0 fallback.
- **ElevenLabs** can generate voiceover or music.
- **AWS S3** is only needed if you use upload helpers in the demo composer.

Never commit `.env`, cookies, generated videos, recordings, or user sessions.

---

## Add It To An Agent

### Cursor Project Skill

Copy the folder into your project:

```bash
mkdir -p .agents/skills
cp -R super-video-maker-skill super-video-maker
```

Then ask your agent:

```text
Use the super-video-maker skill to create an avatar explainer about this topic...
```

### Claude Code / Other Agentic Frameworks

Place `SKILL.md` and the supporting files wherever your framework loads skills or system prompts from. The important part is that the agent can read:

- `SKILL.md`,
- `REFERENCE.md`,
- `WORKFLOW_EXAMPLES.md`,
- `FFMPEG_PLAYBOOK.md`,
- `REMOTION_VIDEO_GUIDE.md`,
- the `tools/` directory.

If your framework does not support skills natively, paste `SKILL.md` into the agent's system prompt and keep the rest of the files in the working directory.

---

## Quick Start: Make An Avatar Explainer

Example prompt to your agent:

```text
Use the super-video-maker skill.

Make a 90-second Avatar Explainer about a trending SEO topic.
Use a recent X.com post as a trend signal, but verify the claims with official sources.
Use my HeyGen avatar.
Use screen/source receipts and UI micro-stories.
Do not make generic AI b-roll.
Pause before paid HeyGen/OpenAI/Replicate calls and show me the plan first.
```

Expected agent flow:

1. Pick the topic and trend signal.
2. Build a source deck with official/corroborating sources.
3. Write the avatar script.
4. Create a storyboard with one visual job per beat: proof, mechanism, consequence, action, or transition.
5. Ask before paid generation.
6. Render the HeyGen avatar.
7. Extract audio and transcribe with word-level timestamps.
8. Generate b-roll/source assets.
9. Run `broll_layout_qc.py`.
10. Compose with FFmpeg or Remotion.
11. Burn centered karaoke captions.
12. Run `ffmpeg_qc.py`.
13. Sample frames and visually review the result.

---

## The Avatar Explainer Recipe

Use `avatar-explainer` when the video combines:

- a synthetic presenter,
- source proof,
- screen recordings or screenshots,
- b-roll that explains the narration,
- UI micro-stories,
- centered captions,
- a spoken CTA ending.

The default structure:

```text
Hook
→ casual avatar disclosure
→ news/update beat
→ concrete example
→ source proof
→ action steps
→ spoken CTA tail over outro card
```

Important rules:

- Say the avatar disclosure in the script after the hook.
- Do not use a static disclaimer slide.
- Put the avatar PiP top-right, borderless, rounded, with a soft drop shadow.
- Keep captions bottom-centered.
- Never place captions and lower-thirds in the same band.
- Beat-lock visual changes to actual Whisper timestamps, not guessed timings.
- Use real screenshots/source receipts before generated b-roll.
- Run layout QC before final composition.

---

## Tool Examples

Generate a HeyGen avatar clip:

```bash
python3 .agents/plugins/super-video-maker-plugin/tools/heygen_client.py \
  --script-file script.txt \
  --output ${PLUGIN_DATA}/jobs/my_job/avatar.mp4 \
  --avatar-id "$HEYGEN_AVATAR_ID" \
  --voice-id "$HEYGEN_VOICE_ID"
```

Generate Seedance b-roll:

```bash
python3 .agents/plugins/super-video-maker-plugin/tools/replicate_video.py generate \
  --prompt "documentary-style browser research shot, source receipt, modern editorial pacing" \
  --duration 7 \
  --resolution 1080p \
  --aspect-ratio 16:9
```

Run b-roll layout QC:

```bash
python3 .agents/plugins/super-video-maker-plugin/tools/broll_layout_qc.py ${PLUGIN_DATA}/jobs/my_job/${PLUGIN_DATA}/assets/*.mp4 --job-dir ${PLUGIN_DATA}/jobs/my_job
```

Run final technical QC:

```bash
python3 .agents/plugins/super-video-maker-plugin/tools/ffmpeg_qc.py ${PLUGIN_DATA}/jobs/my_job/final/master.mp4
```

---

## B-Roll Taste Rules

The skill strongly avoids generic "AI slop." A good visual answers:

```text
What state change should the viewer understand at this sentence?
```

Good visual choices:

- official source screenshots,
- exact paragraph crops,
- browser proof recordings,
- UI before/after states,
- headline walls,
- source receipt cards,
- action cards,
- dashboards,
- calendars,
- CMS editors,
- docs, spreadsheets, or SERPs where the work actually happens.

Bad visual choices:

- random person at a laptop,
- glowing AI brain,
- neon grid,
- floating icons,
- generic data streams,
- repeated website hero crops,
- slow scrolling with no new evidence.

---

## Quality Gates

Every serious video should pass:

- **Paid-call gate:** before HeyGen/OpenAI/Replicate calls, show planned providers, count, duration, resolution, and cost drivers.
- **Source-deck gate:** every major claim has a receipt or clear source.
- **Timestamp gate:** visuals and captions are locked to actual audio timestamps.
- **Layout gate:** `broll_layout_qc.py` confirms no PiP/caption collisions.
- **Technical gate:** `ffmpeg_qc.py` confirms stream, duration, codec, audio, resolution, and black-frame checks.
- **Human/vision gate:** sample final frames and inspect them like a viewer.

---

## Included Templates

### The Zero-Build Master Engine (`remotion-app/`)

This workspace uses a data-driven rendering engine. Agents do not write `.tsx` files. Instead, they produce a `05_blueprint.json` which the Master Engine dynamically parses to mount components from the `template-registry.tsx`.

To preview a project (requires `materialize_project.py` to be run first):
```bash
python scripts/open_studio.py <project_id>
```

To render the final MP4 (requires `.studio_approved` flag file):
```bash
python scripts/render_project.py <project_id>
```

---

## Recommended Agent Prompt

```text
Use the super-video-maker skill.

Goal: create a polished Avatar Explainer.
Length: 90 seconds.
Format: 16:9.
Presenter: HeyGen avatar.
Style: source receipts, UI micro-stories, fast editorial pacing, centered captions.

Before paid calls:
- show the source deck,
- show the script,
- show the storyboard,
- list the paid generation calls and cost drivers.

After generation:
- transcribe the audio,
- align visuals to Whisper timestamps,
- run b-roll layout QC,
- run final FFmpeg QC,
- sample frames and visually inspect the result.
```

---

## Safety And Ethics

- Disclose synthetic presenters.
- Do not fake screenshots, tweets, source receipts, or publication claims.
- Do not publish private avatar IDs, session cookies, tokens, or generated user media.
- Avoid copyright-infringing visual prompts or copied channel styles.
- Use generated visuals as explanation, not deception.
- Prefer official sources for news/SEO/finance/health claims.

---

## Roadmap Ideas

- One-command `video_orchestrator.py` recipe runner for `avatar-explainer`.
- Built-in HTML source receipt renderer.
- Browser-based review dashboard for b-roll layout QC.
- Optional auto-upload adapters for YouTube, LinkedIn, TikTok, and X.
- More Remotion components for proof cards, source decks, and action cards.

---

## Built By Distribb

Distribb helps founders and operators build SEO systems: keyword research, original data research, content publishing, internal linking, backlinks, and content repurposing.

Learn more at [distribb.io](https://distribb.io).
