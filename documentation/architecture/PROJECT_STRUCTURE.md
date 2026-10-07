# شجرة ملفات مشروع Clean Video Workspace

> **تاريخ التوليد:** 2026-09-18  
> **مسار جذر المشروع:** `c:\video\clean-video-workspace`  
> **الحالة:** تم تطبيق كافة معايير الفلترة الدقيقة المطلوبة من قِبل المستخدم.

---

## 📌 معايير التصفية والاستثناءات المطبقة

تم توليد هذه الشجرة وفق شروط دقيقة وصارمة لتفادي الحشو الهائل وتوفير نظرة برمجية ومعمارية فائقة النقاء:

1. 🚫 **استثناء المكتبات البرمجية الثقيلة (Heavy Libraries Excluded):**
   - **مجلدات `node_modules` العامة:** تم حجب عشرات الآلاف من الملفات والمكتبات العامة (مثل React, Babel, Webpack, Esbuild, TypeScript, Vitest, MapLibre, Turf وغيرها).
   - **بيئات العمل الافتراضية بايثون (`.venv`):** تم استثناء بيئة الجذر بالإضافة إلى جميع بيئات `.venv` التابعة لخوادم أدوات الـ MCP (مثل `media-sources-mcp`, `audio-tools-mcp`, `video-tools-mcp`, `image-tools-mcp` التي كانت تحوي آلاف الملفات الحزمية).
   - **كاش وملفات التشغيل المؤقتة:** تم استبعاد مجلدات `.git`, `.pytest_cache`, `.remediation`, `logs/`, `scratch/`, `__pycache__`, وملفات البايت كود `*.pyc` وملفات خرائط المصدر `*.map`.

2. 🚫 **استثناء المشاريع التجريبية (Experimental Projects Excluded):**
   - تم استثناء المئات من مجلدات المشاريع المولدة آلياً ومشاريع الاختبار التجريبية (`projects/prj_*`, `projects/test-*`, `remotion-app/projects/*`, `public/projects/*`).

3. 🚫 **استثناء ملفات الوسائط الميديا (Media Files Excluded):**
   - تم استثناء كافة ملفات الميديا الموجودة بجميع أنواعها (فيديو: `.mp4`, `.mov`، صوتيات ومؤثرات: `.mp3`, `.wav`، صور وأيقونات: `.png`, `.jpg`, `.svg`, `.webp`, إلخ).
   - تم الحفاظ على أسماء وهيكل المجلدات الحاضنة لتوضيح بنيتها التنظيمية، مع الإبقاء على ملفات الميتاداتا البرمجية ذات الصلة (مثل ملفات فحص الصوت `.analysis.json`).

4. ✅ **تضمين مكتبات القوالب الموجودة داخل مجلدات Node (Template Libraries Preserved):**
   - تم فحص وتضمين مكتبات القوالب ومكونات الفيديو المعيارية المتواجدة داخل `node_modules`:
     - **`node_modules/remotion-bits`:** مكتبة مكونات ريموشن وقوالب الرسوم المتحركة (تتضمن `src/components/`, `src/catalog/`, `registry.json`, وأمثلة القوالب في `docs/src/bits/examples/`).
     - **`remotion-app/node_modules/remotion-ui`:** مكتبة القوالب البرمجية ومكونات واجهة ريموشن (تتضمن `templates/`, `dist/registry/`, `dist/schema/`).

---

## 🏛️ ملخص الوحدات والمجلدات الأساسية في النظام

| المجلد / الملف | الدور الوظيفي في خط الإنتاج |
| :--- | :--- |
| **`.agents/`** | قواعد توجيه وكلاء الذكاء الاصطناعي (Directives)، حراس الأمان (Guardian)، والمهارات البرمجية المعتمدة (`remocn`, `snapcn`, إلخ). |
| **`api/`** | الخادم الخلفي القائم على FastAPI لإدارة دورة حياة المشاريع والعمليات. |
| **`assets/`** | مستودع الأصول المنظمة (أصوات، فيديو، أيقونات، موسيقى، تعليق صوتي) قبل دمجه بالمشاريع. |
| **`config/`** | إعدادات النظام ومصفوفات التوقيت وبوابات الذوق. |
| **`contracts/`** | عقود النظام التوافقية ومخططات تدفق البيانات وبلوبرينت المشاهد (`05_blueprint.json`). |
| **`documentation/`** | الوثائق المعمارية، بوابات الجودة (QC Gates)، وتحليل النظم الفرعية للرندرة. |
| **`ground-truth/`** | المواصفات القياسية والعينات المرجعية المؤكدة برمجياً. |
| **`recipes/`** | وصفات خطوط الإنتاج والسيناريوهات المحددة مسبقاً. |
| **`references/`** | المراجع والأدلة المساعدة، ومصفوفة ربط المؤثرات الصوتية والخطوط (`SFX_BINDING_MATRIX.md`). |
| **`registry/`** | سجل القوالب والمؤثرات المركزي (`template-registry.tsx`, `effects-catalog.ts`, `tier-map.json`). |
| **`remotion-app/`** | محرك ريموشن الفعلي، ويحتوي على مغلفات القوالب (`templates/elements/`, `templates/scenes/`) والتركيبات. |
| **`schemas/`** | مخططات التحقق من صحة البيانات (Pydantic و JSON Schemas). |
| **`scripts/`** | المحرك الأساسي لأتمتة خط الإنتاج (`pipeline.py`, `render_project.py`, بوابات QC، والمتحققات). |
| **`templates/`** | القوالب البرمجية الأصلية مقسمة إلى عناصر ومؤثرات ومشاهد (`custom`, `effects`, `elements`, `scenes`). |
| **`tests/`** | حزم الاختبارات الآلية (عقود، ريموشن، أمان، تكامل). |
| **`التعلم/`** | ملفات المعرفة والمذكرات المعمارية للتعلم المستمر للنظام. |

---

## 🌲 هيكل شجرة الملفات الكامل (File Tree)

```text
clean-video-workspace/
├── .agents/
│   ├── docker/
│   │   └── Dockerfile.remotion
│   ├── guardian/
│   │   ├── behavior_guard.py
│   │   ├── circuit_breaker.json
│   │   ├── command_guard.py
│   │   ├── post_executor.py
│   │   ├── utils.py
│   │   └── write_guard.py
│   ├── plugins/
│   │   └── super-video-maker-plugin/
│   │       ├── commands/
│   │       │   └── avatar-insta-reel.md
│   │       ├── reference/
│   │       │   └── ground-truth/
│   │       │       └── template_catalog.json
│   │       ├── skills/
│   │       │   ├── remocn/
│   │       │   │   ├── references/
│   │       │   │   │   ├── archetypes/
│   │       │   │   │   │   ├── changelog.md
│   │       │   │   │   │   ├── cli-tool-demo.md
│   │       │   │   │   │   ├── feature-announcement.md
│   │       │   │   │   │   ├── index.md
│   │       │   │   │   │   ├── logo-bumper.md
│   │       │   │   │   │   ├── oss-showcase.md
│   │       │   │   │   │   ├── pricing-reveal.md
│   │       │   │   │   │   ├── product-demo.md
│   │       │   │   │   │   ├── testimonial-reel.md
│   │       │   │   │   │   └── year-in-review.md
│   │       │   │   │   └── anatomy.md
│   │       │   │   └── SKILL.md
│   │       │   ├── snapcn/
│   │       │   │   ├── references/
│   │       │   │   │   ├── archetypes/
│   │       │   │   │   │   ├── changelog.md
│   │       │   │   │   │   ├── cli-tool-demo.md
│   │       │   │   │   │   ├── feature-announcement.md
│   │       │   │   │   │   ├── index.md
│   │       │   │   │   │   ├── logo-bumper.md
│   │       │   │   │   │   ├── oss-showcase.md
│   │       │   │   │   │   ├── pricing-reveal.md
│   │       │   │   │   │   ├── product-demo.md
│   │       │   │   │   │   ├── testimonial-reel.md
│   │       │   │   │   │   └── year-in-review.md
│   │       │   │   │   ├── components/
│   │       │   │   │   │   ├── announce-title.md
│   │       │   │   │   │   ├── answer-stream.md
│   │       │   │   │   │   ├── block-wordmark.md
│   │       │   │   │   │   ├── caret.md
│   │       │   │   │   │   ├── follower-rush.md
│   │       │   │   │   │   ├── hero-launch.md
│   │       │   │   │   │   ├── index.md
│   │       │   │   │   │   ├── input.md
│   │       │   │   │   │   ├── karaoke-captions.md
│   │       │   │   │   │   ├── laptop-frame.md
│   │       │   │   │   │   ├── logo-assemble.md
│   │       │   │   │   │   ├── logo-flicker.md
│   │       │   │   │   │   ├── moodboard-reveal.md
│   │       │   │   │   │   ├── orbit-gallery.md
│   │       │   │   │   │   ├── phone-frame.md
│   │       │   │   │   │   ├── prompt-zoom.md
│   │       │   │   │   │   ├── pulsing-border.md
│   │       │   │   │   │   ├── search-typing.md
│   │       │   │   │   │   ├── snap-cn-ui.md
│   │       │   │   │   │   ├── status-cycle.md
│   │       │   │   │   │   ├── terminal-simulator.md
│   │       │   │   │   │   ├── text-build.md
│   │       │   │   │   │   ├── text-highlight.md
│   │       │   │   │   │   ├── text-reveal.md
│   │       │   │   │   │   ├── text-swap.md
│   │       │   │   │   │   ├── text-swell.md
│   │       │   │   │   │   ├── word-captions.md
│   │       │   │   │   │   └── word-flip.md
│   │       │   │   │   ├── anatomy.md
│   │       │   │   │   ├── anti-patterns.md
│   │       │   │   │   ├── design.md
│   │       │   │   │   └── motion-principles.md
│   │       │   │   └── SKILL.md
│   │       │   └── INDEX.md
│   │       ├── tools/
│   │       │   ├── mcp-servers/
│   │       │   │   ├── audio-tools-mcp/
│   │       │   │   │   ├── src/
│   │       │   │   │   │   └── audio_tools_mcp/
│   │       │   │   │   │       └── __init__.py
│   │       │   │   │   ├── utils/
│   │       │   │   │   │   ├── ffmpeg_ops.py
│   │       │   │   │   │   ├── manifest_builder.py
│   │       │   │   │   │   ├── sentence_splitter.py
│   │       │   │   │   │   ├── timeline_builder.py
│   │       │   │   │   │   └── voiceover_ops.py
│   │       │   │   │   ├── .device_capability.json
│   │       │   │   │   ├── .gitignore
│   │       │   │   │   ├── .python-version
│   │       │   │   │   ├── complex_test_result.json
│   │       │   │   │   ├── pyproject.toml
│   │       │   │   │   ├── README.md
│   │       │   │   │   ├── server.py
│   │       │   │   │   ├── test_result.json
│   │       │   │   │   ├── uv.lock
│   │       │   │   │   └── voiceover_manifest.json
│   │       │   │   ├── common-tools-mcp/
│   │       │   │   │   ├── src/
│   │       │   │   │   │   └── common_tools_mcp/
│   │       │   │   │   │       └── __init__.py
│   │       │   │   │   ├── utils/
│   │       │   │   │   │   └── cache_ops.py
│   │       │   │   │   ├── .gitignore
│   │       │   │   │   ├── .python-version
│   │       │   │   │   ├── pyproject.toml
│   │       │   │   │   ├── README.md
│   │       │   │   │   ├── server.py
│   │       │   │   │   └── uv.lock
│   │       │   │   ├── ffmpeg-mcp-server/
│   │       │   │   │   ├── scripts/
│   │       │   │   │   │   └── .gitkeep
│   │       │   │   │   ├── test/
│   │       │   │   │   │   └── .gitkeep
│   │       │   │   │   ├── .gitignore
│   │       │   │   │   ├── Dockerfile
│   │       │   │   │   ├── LICENSE
│   │       │   │   │   ├── package-lock.json
│   │       │   │   │   ├── package.json
│   │       │   │   │   ├── README.md
│   │       │   │   │   └── server.js
│   │       │   │   ├── image-tools-mcp/
│   │       │   │   │   ├── src/
│   │       │   │   │   │   └── image_tools_mcp/
│   │       │   │   │   │       └── __init__.py
│   │       │   │   │   ├── utils/
│   │       │   │   │   │   └── image_ops.py
│   │       │   │   │   ├── .gitignore
│   │       │   │   │   ├── .python-version
│   │       │   │   │   ├── pyproject.toml
│   │       │   │   │   ├── README.md
│   │       │   │   │   ├── server.py
│   │       │   │   │   └── uv.lock
│   │       │   │   ├── media-sources-mcp/
│   │       │   │   │   ├── src/
│   │       │   │   │   │   └── media_sources_mcp/
│   │       │   │   │   │       └── __init__.py
│   │       │   │   │   ├── tools/
│   │       │   │   │   │   ├── freesound.py
│   │       │   │   │   │   ├── iconify.py
│   │       │   │   │   │   ├── pexels.py
│   │       │   │   │   │   └── pixabay.py
│   │       │   │   │   ├── utils/
│   │       │   │   │   │   ├── downloader.py
│   │       │   │   │   │   ├── file_organizer.py
│   │       │   │   │   │   ├── http_client.py
│   │       │   │   │   │   └── pixabay_scraper.py
│   │       │   │   │   ├── .env.example
│   │       │   │   │   ├── .gitignore
│   │       │   │   │   ├── .python-version
│   │       │   │   │   ├── dump.html
│   │       │   │   │   ├── dump_html.py
│   │       │   │   │   ├── pyproject.toml
│   │       │   │   │   ├── pyrightconfig.json
│   │       │   │   │   ├── README.md
│   │       │   │   │   ├── server.py
│   │       │   │   │   ├── test_attrs.py
│   │       │   │   │   ├── test_click.py
│   │       │   │   │   ├── test_internal_api.py
│   │       │   │   │   ├── test_network.py
│   │       │   │   │   ├── test_pix.py
│   │       │   │   │   ├── test_playwright.py
│   │       │   │   │   ├── test_regex.py
│   │       │   │   │   ├── test_scrape.py
│   │       │   │   │   ├── test_workflow.py
│   │       │   │   │   ├── test_workflow_final.py
│   │       │   │   │   └── uv.lock
│   │       │   │   └── video-tools-mcp/
│   │       │   │       ├── src/
│   │       │   │       │   └── video_tools_mcp/
│   │       │   │       │       └── __init__.py
│   │       │   │       ├── utils/
│   │       │   │       │   └── ffmpeg_ops.py
│   │       │   │       ├── .gitignore
│   │       │   │       ├── .python-version
│   │       │   │       ├── pyproject.toml
│   │       │   │       ├── README.md
│   │       │   │       ├── server.py
│   │       │   │       └── uv.lock
│   │       │   ├── ad_quality_gate.py
│   │       │   ├── agent_browser_recorder.py
│   │       │   ├── broll_layout_qc.py
│   │       │   ├── elevenlabs_voice.py
│   │       │   ├── fal_seedance_video.py
│   │       │   ├── ffmpeg_qc.py
│   │       │   ├── heygen_client.py
│   │       │   ├── image_provider.py
│   │       │   ├── media_pipeline.py
│   │       │   ├── music_provider.py
│   │       │   ├── replicate_video.py
│   │       │   ├── screen_recorder.py
│   │       │   └── video_captioner.py
│   │       ├── .gitignore
│   │       ├── mcp_config.json
│   │       ├── package.json
│   │       ├── plugin.json
│   │       └── verify.py
│   ├── rules/
│   │   └── video-production-protocol.md
│   ├── secrets/
│   │   └── .qc_salt
│   ├── skills/
│   │   └── prompt-engineering-expert/
│   │       ├── docs/
│   │       │   ├── BEST_PRACTICES.md
│   │       │   ├── TECHNIQUES.md
│   │       │   └── TROUBLESHOOTING.md
│   │       ├── examples/
│   │       │   └── EXAMPLES.md
│   │       ├── .author
│   │       ├── _meta.json
│   │       ├── CLAUDE.md
│   │       ├── GETTING_STARTED.md
│   │       ├── INDEX.md
│   │       ├── README.md
│   │       ├── SKILL.md
│   │       ├── START_HERE.md
│   │       └── SUMMARY.md
│   └── AGENTS.md
├── .githooks/
│   ├── pre-commit
│   └── pre-push
├── .github/
│   ├── workflows/
│   │   └── remediation-ci.yml
│   └── pull_request_template.md
├── .ruff_cache/
│   ├── 0.16.9/
│   │   ├── 11146449423985839785
│   │   ├── 1443882394304167195
│   │   ├── 14581171327088233129
│   │   ├── 15103414814778688205
│   │   ├── 16018067529820871031
│   │   ├── 1670238224281776031
│   │   ├── 2004999474540353788
│   │   ├── 2035401221175205119
│   │   ├── 3258635172741283491
│   │   ├── 37312795544118831
│   │   ├── 4441111942134976163
│   │   ├── 5575643253230673647
│   │   ├── 7573001201057708114
│   │   ├── 8731448460503571558
│   │   └── 9804975019108247730
│   ├── .gitignore
│   └── CACHEDIR.TAG
├── ai/
│   ├── acquisition/
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── freesound.py
│   │   │   ├── iconify.py
│   │   │   ├── pexels.py
│   │   │   └── pixabay.py
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   ├── dedupe.py
│   │   ├── errors.py
│   │   ├── filtering.py
│   │   ├── ranking.py
│   │   ├── safe_downloader.py
│   │   └── service.py
│   ├── audio/
│   │   ├── benchmark/
│   │   │   ├── __init__.py
│   │   │   ├── fixtures.py
│   │   │   ├── manifest.py
│   │   │   ├── metrics.py
│   │   │   └── runner.py
│   │   ├── __init__.py
│   │   ├── dsp.py
│   │   ├── modes.py
│   │   └── pipeline.py
│   ├── batch/
│   │   ├── __init__.py
│   │   ├── policy.py
│   │   └── service.py
│   ├── budget/
│   │   ├── __init__.py
│   │   ├── accounting.py
│   │   ├── estimator.py
│   │   ├── policy.py
│   │   ├── repository.py
│   │   ├── reservation.py
│   │   ├── service.py
│   │   └── types.py
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── errors.py
│   │   ├── key.py
│   │   ├── policy.py
│   │   ├── repository.py
│   │   └── service.py
│   ├── candidates/
│   │   ├── gates/
│   │   │   ├── __init__.py
│   │   │   ├── aspect_gate.py
│   │   │   ├── ast_runner.py
│   │   │   ├── base.py
│   │   │   ├── candidate_qc_gate.py
│   │   │   ├── contract_gate.py
│   │   │   ├── dependency_gate.py
│   │   │   ├── probe_gate.py
│   │   │   ├── render_smoke_gate.py
│   │   │   ├── runtime_contract_gate.py
│   │   │   ├── security_gate.py
│   │   │   ├── static_code_gate.py
│   │   │   ├── template_schema_gate.py
│   │   │   └── typescript_gate.py
│   │   ├── __init__.py
│   │   ├── errors.py
│   │   ├── hashing.py
│   │   ├── policies.py
│   │   ├── promotion_service.py
│   │   ├── repository.py
│   │   ├── review_service.py
│   │   ├── runtime_runner.py
│   │   ├── service.py
│   │   └── validation_service.py
│   ├── capabilities/
│   │   ├── __init__.py
│   │   ├── catalog.py
│   │   ├── definitions.py
│   │   ├── registry.py
│   │   └── types.py
│   ├── conflict/
│   │   ├── __init__.py
│   │   └── resolver.py
│   ├── context/
│   │   ├── __init__.py
│   │   ├── assembly.py
│   │   ├── budgeting.py
│   │   ├── builder.py
│   │   ├── compression.py
│   │   ├── deduplication.py
│   │   ├── needs.py
│   │   ├── ranking.py
│   │   ├── retrieval.py
│   │   └── types.py
│   ├── contracts/
│   │   ├── creative/
│   │   │   ├── __init__.py
│   │   │   ├── brief.py
│   │   │   ├── conflict.py
│   │   │   ├── cost.py
│   │   │   ├── directors.py
│   │   │   ├── feedback.py
│   │   │   ├── narrative.py
│   │   │   ├── plan.py
│   │   │   ├── recipe.py
│   │   │   ├── regression.py
│   │   │   ├── skills_knowledge.py
│   │   │   ├── taste.py
│   │   │   └── template_candidate.py
│   │   ├── __init__.py
│   │   ├── activity.py
│   │   ├── audio.py
│   │   ├── base.py
│   │   ├── cache.py
│   │   ├── capability.py
│   │   ├── common.py
│   │   ├── errors.py
│   │   ├── evals.py
│   │   ├── media.py
│   │   ├── media_ops.py
│   │   ├── memory.py
│   │   ├── model.py
│   │   ├── observability.py
│   │   ├── prompt.py
│   │   ├── request.py
│   │   ├── response.py
│   │   ├── run.py
│   │   ├── specialized.py
│   │   ├── tools.py
│   │   ├── usage.py
│   │   └── vision.py
│   ├── cost/
│   │   ├── __init__.py
│   │   ├── accounting.py
│   │   ├── analyzer.py
│   │   ├── baseline.py
│   │   ├── collector.py
│   │   └── errors.py
│   ├── directors/
│   │   ├── __init__.py
│   │   ├── bundle.py
│   │   ├── emotion_director.py
│   │   ├── motion_director.py
│   │   ├── narrative_director.py
│   │   └── sfx_director.py
│   ├── evals/
│   │   ├── __init__.py
│   │   ├── creative_datasets.py
│   │   ├── creative_evals_s28_04.py
│   │   ├── datasets.py
│   │   ├── deferred.py
│   │   ├── evaluators.py
│   │   ├── gate.py
│   │   ├── promotion.py
│   │   └── runner.py
│   ├── feedback/
│   │   ├── __init__.py
│   │   ├── classifier.py
│   │   └── service.py
│   ├── image_processing/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   ├── cache.py
│   │   ├── contracts.py
│   │   ├── errors.py
│   │   ├── security.py
│   │   ├── service.py
│   │   └── validator.py
│   ├── intent/
│   │   ├── __init__.py
│   │   ├── brief_builder.py
│   │   ├── contracts.py
│   │   ├── evaluator.py
│   │   └── parser.py
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   ├── indexer.py
│   │   ├── loader.py
│   │   ├── registry.py
│   │   ├── retriever.py
│   │   ├── router.py
│   │   └── semantic.py
│   ├── mcp/
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── audio.py
│   │   │   ├── base.py
│   │   │   ├── image.py
│   │   │   ├── parity.py
│   │   │   └── video.py
│   │   ├── compatibility/
│   │   │   ├── __init__.py
│   │   │   ├── contracts.py
│   │   │   ├── facade.py
│   │   │   ├── mappers.py
│   │   │   ├── registry.py
│   │   │   └── server.py
│   │   ├── __init__.py
│   │   ├── audit.py
│   │   ├── catalog.py
│   │   ├── contracts.py
│   │   ├── errors.py
│   │   └── policy.py
│   ├── media/
│   │   ├── __init__.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── technical_probe.py
│   │   └── validation.py
│   ├── media_processing/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   ├── contracts.py
│   │   ├── errors.py
│   │   ├── security.py
│   │   ├── service.py
│   │   ├── staging.py
│   │   └── validator.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── deduplication.py
│   │   ├── embeddings.py
│   │   ├── facade.py
│   │   ├── models.py
│   │   ├── normalization.py
│   │   ├── policy.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── types.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── definitions.py
│   │   ├── registry.py
│   │   └── types.py
│   ├── narrative/
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   ├── metrics.py
│   │   └── planner.py
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   ├── redaction.py
│   │   ├── repository.py
│   │   └── tracer.py
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── activity.py
│   │   ├── activity_classification.py
│   │   ├── dag.py
│   │   ├── errors.py
│   │   ├── lease.py
│   │   ├── recovery.py
│   │   ├── repository.py
│   │   ├── retry.py
│   │   ├── service.py
│   │   ├── state.py
│   │   └── worker.py
│   ├── planning/
│   │   ├── __init__.py
│   │   ├── asset_preparation.py
│   │   ├── compiler.py
│   │   ├── compose_engine.py
│   │   ├── creative_planner.py
│   │   ├── errors.py
│   │   ├── reuse_engine.py
│   │   ├── tier_policy.py
│   │   └── validator.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── repository.py
│   │   └── service.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── definitions.py
│   │   ├── fake.py
│   │   ├── openrouter.py
│   │   └── registry.py
│   ├── recipes/
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   ├── evaluator.py
│   │   ├── registry.py
│   │   └── selector.py
│   ├── regression/
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   ├── datasets.py
│   │   ├── retrieval_grader.py
│   │   ├── rubric_grader.py
│   │   ├── runner.py
│   │   └── trace_grader.py
│   ├── routing/
│   │   ├── __init__.py
│   │   ├── capability_router.py
│   │   ├── constraints.py
│   │   ├── cost.py
│   │   ├── escalation.py
│   │   ├── fallback.py
│   │   ├── policy.py
│   │   ├── router.py
│   │   ├── scoring.py
│   │   └── types.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── bounds.py
│   │   ├── policies.py
│   │   ├── scrubber.py
│   │   └── ssrf.py
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── context.py
│   │   ├── contracts.py
│   │   ├── loader.py
│   │   ├── registry.py
│   │   └── router.py
│   ├── specialized/
│   │   ├── __init__.py
│   │   ├── adapters.py
│   │   ├── errors.py
│   │   ├── interfaces.py
│   │   └── service.py
│   ├── speech/
│   │   ├── benchmark/
│   │   │   ├── __init__.py
│   │   │   ├── corpus_manifest.py
│   │   │   ├── metrics.py
│   │   │   └── runner.py
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   ├── cache.py
│   │   ├── lifecycle.py
│   │   ├── local_provider.py
│   │   ├── manifest.py
│   │   ├── preparation.py
│   │   ├── reconciliation.py
│   │   ├── storage_resolver.py
│   │   ├── stt_provider.py
│   │   └── timeline.py
│   ├── style/
│   │   ├── __init__.py
│   │   └── resolver.py
│   ├── taste/
│   │   ├── __init__.py
│   │   ├── context.py
│   │   ├── contracts.py
│   │   ├── engine.py
│   │   ├── evaluator.py
│   │   └── registry.py
│   ├── tools/
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── acquisition.py
│   │   │   ├── base.py
│   │   │   ├── domain_service.py
│   │   │   ├── image_processing.py
│   │   │   ├── mcp.py
│   │   │   ├── media_processing.py
│   │   │   ├── native.py
│   │   │   ├── registry.py
│   │   │   ├── remote.py
│   │   │   └── worker.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── assets.py
│   │   │   ├── blueprint.py
│   │   │   ├── projects.py
│   │   │   ├── qc.py
│   │   │   └── runs.py
│   │   ├── __init__.py
│   │   ├── audit.py
│   │   ├── authorization.py
│   │   ├── contracts.py
│   │   ├── dispatcher.py
│   │   ├── errors.py
│   │   ├── gateway.py
│   │   ├── registry.py
│   │   └── types.py
│   ├── vision/
│   │   ├── benchmark/
│   │   │   ├── __init__.py
│   │   │   ├── manifest.py
│   │   │   ├── metrics.py
│   │   │   └── runner.py
│   │   ├── __init__.py
│   │   ├── adaptive_resolution.py
│   │   ├── keyframe_extractor.py
│   │   ├── object_person.py
│   │   ├── ocr.py
│   │   ├── pipeline.py
│   │   └── shot_detection.py
│   └── __init__.py
├── api/
│   ├── core/
│   │   ├── auth.py
│   │   ├── config.py
│   │   └── errors.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── artifacts.py
│   │   ├── assets.py
│   │   ├── authoring.py
│   │   ├── blueprint.py
│   │   ├── brand.py
│   │   ├── candidate_promotions.py
│   │   ├── candidate_reviews.py
│   │   ├── gates.py
│   │   ├── health.py
│   │   ├── outputs.py
│   │   ├── projects.py
│   │   ├── render.py
│   │   └── runs.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── artifact.py
│   │   ├── asset.py
│   │   ├── blueprint.py
│   │   ├── gate.py
│   │   ├── lifecycle.py
│   │   ├── project.py
│   │   ├── responses.py
│   │   └── run.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── asset_service.py
│   │   ├── authoring_service.py
│   │   ├── brand_service.py
│   │   ├── domain_artifact_service.py
│   │   ├── gate_service.py
│   │   ├── health_service.py
│   │   ├── output_service.py
│   │   ├── override_service.py
│   │   ├── pipeline_service.py
│   │   ├── project_service.py
│   │   ├── render_service.py
│   │   ├── run_service.py
│   │   └── scaffold_service.py
│   ├── __init__.py
│   ├── main.py
│   ├── README.md
│   └── websocket.py
├── assets/
│   ├── cache/
│   │   └── .gitkeep
│   ├── incoming/
│   │   ├── legasy/  [مجلد وسائط مستثناة أو فارغ]
│   │   ├── tests/
│   │   │   ├── .human_vo_01_0f62dbc8.analysis.json
│   │   │   └── human_vo_01.txt
│   │   ├── .gitkeep
│   │   ├── .الموبايل الي بايدك_0d300042.analysis.json
│   │   ├── .الموبايل الي بايدك_norm_954726a6.analysis.json
│   │   ├── .تحدي الثلاثين يوما_206ec956.analysis.json
│   │   ├── .تحدي بايثون_1bf6b023.analysis.json
│   │   ├── .تعلم البرمجة_206ec956.analysis.json
│   │   └── .عالم التقنية_e872816a.analysis.json
│   ├── processing/
│   │   ├── phone_power_sentences/  [مجلد وسائط مستثناة أو فارغ]
│   │   ├── prj_c05b1800_sentences/  [مجلد وسائط مستثناة أو فارغ]
│   │   └── .gitkeep
│   └── ready/
│       ├── audio/  [مجلد وسائط مستثناة أو فارغ]
│       ├── icons/
│       │   ├── cpu_solar/  [مجلد وسائط مستثناة أو فارغ]
│       │   ├── crescent_moon_noto.svg/  [مجلد وسائط مستثناة أو فارغ]
│       │   ├── light_bulb_noto.svg/  [مجلد وسائط مستثناة أو فارغ]
│       │   ├── meteor_pkg/  [مجلد وسائط مستثناة أو فارغ]
│       │   ├── rocket.svg/  [مجلد وسائط مستثناة أو فارغ]
│       │   ├── rocket_noto.svg/  [مجلد وسائط مستثناة أو فارغ]
│       │   ├── satellite_solar.svg/  [مجلد وسائط مستثناة أو فارغ]
│       │   └── shuttle_pkg/  [مجلد وسائط مستثناة أو فارغ]
│       ├── music/  [مجلد وسائط مستثناة أو فارغ]
│       ├── other/  [مجلد وسائط مستثناة أو فارغ]
│       ├── sfx/  [مجلد وسائط مستثناة أو فارغ]
│       ├── video/  [مجلد وسائط مستثناة أو فارغ]
│       ├── vo/
│       │   ├── .mobile_nasa_vo_norm_954726a6.analysis.json
│       │   └── .تحدي_الثلاثين_يوما_norm_bfbebf71.analysis.json
│       └── .gitkeep
├── authoring/
│   ├── creative-adapter.ts
│   ├── index.ts
│   ├── intent-planner.ts
│   ├── template-adapter.ts
│   └── unified-authoring-session.ts
├── canvas/
│   ├── canvas-renderer-adapter.ts
│   └── index.ts
├── compositor/
│   ├── audio-normalizer.ts
│   ├── index.ts
│   ├── master-compositor.ts
│   ├── output-normalizer.ts
│   ├── probe.ts
│   ├── qc-adapter.ts
│   └── timeline-assembler.ts
├── config/
│   ├── violations_config.json
│   └── violations_config.schema.json
├── contracts/
│   ├── fixtures/
│   │   └── asset_resolution_golden.json
│   ├── generated/
│   │   ├── ai_contracts.ts
│   │   └── creative_contracts.ts
│   ├── animations.ts
│   ├── asset-resolver.ts
│   ├── authoring.ts
│   ├── blueprint.ts
│   ├── brand.ts
│   ├── canonical-video.ts
│   ├── compositor.ts
│   ├── editor-session.ts
│   ├── effects.ts
│   ├── evaluator.ts
│   ├── fonts.ts
│   ├── index.ts
│   ├── keyframes.ts
│   ├── layers.ts
│   ├── manifest.ts
│   ├── mutations.ts
│   ├── normalization.ts
│   ├── override-validator.ts
│   ├── positions.ts
│   ├── preview-fidelity.ts
│   ├── preview-proxy.ts
│   ├── render-graph.ts
│   ├── render-input.ts
│   ├── renderer.ts
│   ├── SceneContent.ts
│   ├── storage-service.ts
│   ├── StyleSurface.ts
│   ├── template-instantiator.ts
│   ├── template-runtime-contract.json
│   ├── template-schemas.ts
│   ├── template-spec.ts
│   ├── timeline.ts
│   └── waveform.ts
├── creative_governance/
│   ├── candidates/
│   │   ├── gates/
│   │   │   ├── __init__.py
│   │   │   ├── aspect_gate.py
│   │   │   ├── ast_runner.py
│   │   │   ├── base.py
│   │   │   ├── candidate_qc_gate.py
│   │   │   ├── contract_gate.py
│   │   │   ├── dependency_gate.py
│   │   │   ├── probe_gate.py
│   │   │   ├── render_smoke_gate.py
│   │   │   ├── runtime_contract_gate.py
│   │   │   ├── security_gate.py
│   │   │   ├── static_code_gate.py
│   │   │   ├── template_schema_gate.py
│   │   │   └── typescript_gate.py
│   │   ├── __init__.py
│   │   ├── errors.py
│   │   ├── hashing.py
│   │   ├── policies.py
│   │   ├── promotion_service.py
│   │   ├── repository.py
│   │   ├── review_service.py
│   │   ├── runtime_runner.py
│   │   ├── service.py
│   │   └── validation_service.py
│   └── __init__.py
├── data/
│   ├── storage/
│   │   ├── system/  [مجلد وسائط مستثناة أو فارغ]
│   │   └── workspaces/
│   │       ├── ws_default/
│   │       │   └── projects/
│   │       │       ├── prj_16979740/
│   │       │       │   └── assets/
│   │       │       │       └── ast_client_logo/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── prj_61839cc6/
│   │       │       │   └── assets/
│   │       │       │       └── ast_client_logo/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── prj_cas_uniqueness/
│   │       │       │   └── assets/
│   │       │       │       └── ast_5a6e9cfab0677c8157db8fd3064752a6c7b5e4cbf6981996c40a890799681a47/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── prj_concurrent_dedupe/
│   │       │       │   └── assets/
│   │       │       │       ├── ast_3bbfa065435da9ff/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       │       └── ast_3bbfa065435da9ff484d5203dc70ffa21ef79ca1bf7f7f39f1ac78e9545ef44b/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── prj_crash_window_recovery/
│   │       │       │   └── assets/
│   │       │       │       └── ast_61ff355b54bfd65c57a02f8b9cf59f8dae0b145185f57b12129858ede032246c/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── prj_e3d01994/
│   │       │       │   └── assets/
│   │       │       │       └── ast_client_logo/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── prj_green_led063/
│   │       │       │   └── assets/
│   │       │       │       └── ast_logo_01/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── prj_same_hash_same_proj/
│   │       │       │   └── assets/
│   │       │       │       └── ast_a619055a34458d21a882dd5870d56c68c7b4acdaff3de144ca1dfaf6126adf77/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── prj_scope_alpha/
│   │       │       │   └── assets/
│   │       │       │       └── ast_f17483575c605c0a641cc8f46305ea9f8e200e998db8bec5185adab9193be468/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       └── prj_scope_beta/
│   │       │           └── assets/
│   │       │               └── ast_f17483575c605c0a641cc8f46305ea9f8e200e998db8bec5185adab9193be468/  [مجلد وسائط مستثناة أو فارغ]
│   │       ├── ws_tenant_corp_1/
│   │       │   └── projects/
│   │       │       └── prj_tenant_corp_1/
│   │       │           └── assets/
│   │       │               └── ast_65c56387b916900e1a988cc9627e3d45a8218a0668a2cecbe15f4f0a3b816d24/  [مجلد وسائط مستثناة أو فارغ]
│   │       └── ws_tenant_corp_2/
│   │           └── projects/
│   │               └── prj_tenant_corp_2/
│   │                   └── assets/
│   │                       └── ast_65c56387b916900e1a988cc9627e3d45a8218a0668a2cecbe15f4f0a3b816d24/  [مجلد وسائط مستثناة أو فارغ]
│   ├── tmp_candidate_runtime/
│   │   ├── cand_rt_cand_1cd3105b03a1_rval_e483af4c1db7_douocnd_/
│   │   │   ├── CandidateComponent.tsx
│   │   │   ├── CandidateHarness.tsx
│   │   │   └── render_props.json
│   │   ├── cand_rt_cand_477b65224727_rval_20a3253deab1_wr_9jpg5/
│   │   │   ├── CandidateComponent.tsx
│   │   │   ├── CandidateHarness.tsx
│   │   │   └── render_props.json
│   │   ├── cand_rt_cand_832e3d23c4de_rval_1d3ee1866dce_ok_vk2ic/
│   │   │   ├── CandidateComponent.tsx
│   │   │   ├── CandidateHarness.tsx
│   │   │   └── render_props.json
│   │   ├── cand_rt_cand_9e814924c1f2_rval_f60760f0bb0d_xv2ikmsy/
│   │   │   ├── CandidateComponent.tsx
│   │   │   ├── CandidateHarness.tsx
│   │   │   └── render_props.json
│   │   ├── cand_rt_cand_ccdf2bdec304_rval_7790fcb0e57d_6m6rvgwg/
│   │   │   ├── CandidateComponent.tsx
│   │   │   ├── CandidateHarness.tsx
│   │   │   └── render_props.json
│   │   └── cand_rt_cand_d26ebb4dacc4_rval_ee229dc862b0_2na9z80h/
│   │       ├── CandidateComponent.tsx
│   │       ├── CandidateHarness.tsx
│   │       └── render_props.json
│   ├── .gitkeep
│   ├── motion.db
│   ├── openrouter_smoke_traces.db
│   └── runs.db
├── documentation/
│   ├── architecture/
│   │   ├── decisions/
│   │   │   ├── ADR-001-single-host-api-worker.md
│   │   │   ├── ADR-002-principal-and-authorization-model.md
│   │   │   ├── ADR-003-multi-tenant-saas-foundation.md
│   │   │   └── ADR-004-ai-media-intelligence-platform.md
│   │   ├── ADR-004-ai-media-intelligence-platform.md
│   │   ├── ai-contract-evolution-policy.md
│   │   ├── ARCHITECTURE_TRUTH.md
│   │   ├── BLUEPRINT_V2_SPEC.md
│   │   ├── MANIFEST_V2_SPEC.md
│   │   ├── PROJECT_STRUCTURE.md
│   │   ├── S27.9-tool-registry-and-authorization.md
│   │   ├── S28-creative-intelligence-foundation.md
│   │   └── TRUST_MODEL.md
│   ├── archive/
│   │   ├── ARCHITECTURE_v1.md
│   │   ├── project_overview.md
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   ├── SYSTEM_OVERVIEW.md
│   │   ├── WORKSPACE_COMPREHENSIVE_GUIDE.md
│   │   └── WORKSPACE_PIPELINE_EXPLAINED.md
│   ├── audits/
│   │   ├── actual_templates_list.txt
│   │   ├── audit_pack.txt
│   │   ├── AUDIT_REPORT.md
│   │   ├── benchmark_real_performance_results.json
│   │   ├── CONFLICTS.md
│   │   ├── creative_cost_audit.json
│   │   ├── creative_regression_run.json
│   │   ├── DECISIONS.md
│   │   ├── EDGE_CASES_REPORT.md
│   │   ├── FINAL_AUDIT_REPORT.md
│   │   ├── FINAL_CHECKLIST.md
│   │   ├── HEALTH.md
│   │   ├── INTEGRATION_TEST_REPORT.md
│   │   ├── INVENTORY.md
│   │   ├── PRE_S25_FULL_VERIFICATION_REPORT.md
│   │   ├── PROJECT_AUDIT_REPORT.md
│   │   ├── PROJECT_RECONNAISSANCE.md
│   │   ├── S27-ai-baseline-inventory.md
│   │   ├── S28-02-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── S28-02A-HYBRID-RETRIEVAL-DELTA-REPORT.md
│   │   ├── S28-03-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── S28-03A-EXIT-GATE-EVIDENCE-DELTA-REPORT.md
│   │   ├── S28-04-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── S28-04A-FINAL-EVIDENCE-DELTA-REPORT.md
│   │   ├── S28-05-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── S28-06-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── S28-06A-FINAL-EVIDENCE-DELTA-REPORT.md
│   │   ├── S28-07A-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── S28-07B-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── S28-07C-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── S28-07D-EXECUTION-EVIDENCE-REPORT.md
│   │   ├── s28_02_eval_report.json
│   │   ├── s28_03_intent_eval_report.json
│   │   ├── s28_03_recipe_eval_report.json
│   │   ├── s28_03a_recipe_compliance_report.json
│   │   ├── s28_04_creative_eval_report.json
│   │   ├── s28_05_planner_eval_report.json
│   │   ├── s28_06_eval_report.json
│   │   ├── s28_full_creative_e2e_run.json
│   │   ├── s28_legacy_creative_inventory.json
│   │   ├── s28_legacy_creative_inventory.md
│   │   ├── SYSTEM_HEALTH_REPORT.md
│   │   ├── TEMPLATE_DISCOVERY.md
│   │   └── TOOL_USAGE_AUDIT.md
│   ├── governance/
│   │   ├── ARCHITECTURE_CHANGE_CONTROL.md
│   │   ├── CHANGE_POLICY.md
│   │   ├── DEFECT_POLICY.md
│   │   ├── DEPENDENCY_POLICY.md
│   │   └── required-checks.md
│   ├── guides/
│   │   ├── DATA_DRIVEN_MIGRATION.md
│   │   ├── SECURITY_PATCH_NOTES.md
│   │   └── UPGRADE_NOTES.md
│   ├── remediation/
│   │   ├── S00_BASELINE_REPORT.md
│   │   ├── S25_FAULT_INJECTION_REPORT.md
│   │   ├── S25_FINAL_ARCHITECTURE_REAUDIT.md
│   │   ├── S25_VERIFICATION_MATRIX.md
│   │   ├── S26_GOVERNANCE_CLOSURE_REPORT.md
│   │   ├── S26_PRODUCTION_GATE.md
│   │   └── S26_REQUIRED_CHECKS_MATRIX.md
│   ├── s28/
│   │   └── evidence/
│   │       ├── testbeds/
│   │       │   ├── creative_datasets_s28_06.py
│   │       │   ├── creative_evals_s28_05.py
│   │       │   └── creative_evals_s28_06.py
│   │       ├── S28-01_REPORT.md
│   │       ├── S28-02_REPORT.md
│   │       ├── S28-03_REPORT.md
│   │       ├── S28-04_REPORT.md
│   │       ├── S28-05_REPORT.md
│   │       ├── S28-06_REPORT.md
│   │       ├── S28-07_FINAL_REPORT.md
│   │       ├── S28-07A_REPORT.md
│   │       ├── S28-07B_REPORT.md
│   │       ├── S28-07C_REPORT.md
│   │       ├── S28-07D_REPORT.md
│   │       ├── S28-07E_REPORT.md
│   │       ├── S28-07F_REPORT.md
│   │       ├── S28-08A_REPORT.md
│   │       ├── S28-08B_REPORT.md
│   │       ├── S28-08C_REPORT.md
│   │       ├── S28-08D_REPORT.md
│   │       ├── S28-08E_REPORT.md
│   │       ├── S28_FINAL_REPORT.md
│   │       └── S28_LEGACY_RETIREMENT.md
│   ├── s28h/
│   │   ├── evidence/
│   │   │   ├── S28-H01_REPORT.md
│   │   │   ├── S28-H02_REPORT.md
│   │   │   └── S28-H03_REPORT.md
│   │   ├── AI_AUTHORITY_MATRIX.md
│   │   ├── AI_OVERLAP_FINDINGS.md
│   │   ├── AI_PACKAGE_DEPENDENCY_GRAPH.md
│   │   ├── AI_PACKAGE_INVENTORY.md
│   │   └── AI_RESTRUCTURE_PROPOSAL.md
│   ├── s28m/
│   │   ├── evidence/
│   │   │   ├── S28-M01_REPORT.md
│   │   │   ├── S28-M02.1_REPORT.md
│   │   │   ├── S28-M02_REPORT.md
│   │   │   ├── S28-M03_REPORT.md
│   │   │   ├── S28-M03_VERIFICATION_CLOSURE.md
│   │   │   ├── S28-M04.1_REPORT.md
│   │   │   ├── S28-M04_REPORT.md
│   │   │   ├── S28-M04_VERIFICATION_CLOSURE.md
│   │   │   ├── S28-M05-C_CLOSURE_REPORT.md
│   │   │   ├── S28-M05_REPORT.md
│   │   │   ├── S28-M06_REPORT.md
│   │   │   ├── S28-M07_REPORT.md
│   │   │   ├── S28-M08_REPORT.md
│   │   │   ├── S28-M09_REPORT.md
│   │   │   ├── S28-M10_REPORT.md
│   │   │   ├── S28-M11_REPORT.md
│   │   │   └── S28-M_FINAL_EVIDENCE_CLOSURE.md
│   │   ├── CAPABILITY_AUTHORITY_MATRIX.md
│   │   ├── CAPABILITY_CATALOG.json
│   │   ├── CAPABILITY_PARITY_MATRIX.json
│   │   ├── CAPABILITY_ROUTING_ARCHITECTURE.md
│   │   ├── CAPABILITY_RUNTIME_MATRIX.md
│   │   ├── CAPABILITY_TAXONOMY.md
│   │   ├── EMBEDDED_MODEL_INVENTORY.json
│   │   ├── FAULT_INJECTION_MATRIX.json
│   │   ├── FINAL_ARCHITECTURE_AUDIT.json
│   │   ├── FINAL_ARCHITECTURE_SEARCH.md
│   │   ├── FINAL_CAPABILITY_MATRIX.json
│   │   ├── LEGACY_TOOL_MIGRATION_MAP.json
│   │   ├── MCP_COMPATIBILITY_MATRIX.json
│   │   ├── MCP_DEPENDENCY_GRAPH.md
│   │   ├── MCP_REALITY_INVENTORY.json
│   │   ├── MCP_TOOL_MATRIX.md
│   │   ├── PERFORMANCE_BASELINE.json
│   │   ├── PRODUCT_E2E_MATRIX.json
│   │   ├── S28-M02_MASTER_REPORT.md
│   │   ├── S28-M_FINAL_REPORT.md
│   │   ├── STT_MODEL_ARCHITECTURE.md
│   │   └── STT_PARITY_MATRIX.md
│   ├── s28r/
│   │   ├── evidence/
│   │   │   ├── R15_BASELINE.md
│   │   │   ├── R15_FAULT_MATRIX.md
│   │   │   ├── R15_FINAL_AUDIT.md
│   │   │   ├── R15_LOAD_SOAK_RESULTS.md
│   │   │   ├── R15_MIGRATION_PARITY_MATRIX.md
│   │   │   ├── S28-R01_REPORT.md
│   │   │   ├── S28-R02_REPORT.md
│   │   │   ├── S28-R03_REPORT.md
│   │   │   ├── S28-R04-PART1_REPORT.md
│   │   │   ├── S28-R04_REPORT.md
│   │   │   ├── S28-R05_REPORT.md
│   │   │   ├── S28-R06_REPORT.md
│   │   │   ├── S28-R07_REPORT.md
│   │   │   ├── S28-R07B_REPORT.md
│   │   │   ├── S28-R08_REPORT.md
│   │   │   ├── S28-R09_REPORT.md
│   │   │   ├── S28-R10_REPORT.md
│   │   │   ├── S28-R11_REPORT.md
│   │   │   ├── S28-R12_REPORT.md
│   │   │   ├── S28-R13_REPORT.md
│   │   │   ├── S28-R14_REPORT.md
│   │   │   └── soak_telemetry_30m.json
│   │   ├── AI_MUTATION_MODEL.md
│   │   ├── AI_USER_EDITING_RULES.md
│   │   ├── ALTERNATIVE_RENDERER_ADAPTER.md
│   │   ├── AUDIO_PREVIEW_RUNTIME.md
│   │   ├── AUDIO_SYNC_MODEL.md
│   │   ├── AUTHORITY_MATRIX.md
│   │   ├── BROWSER_LIVE_PREVIEW_RUNTIME.md
│   │   ├── CANONICAL_MUTATION_MODEL.md
│   │   ├── CANONICAL_NORMALIZATION.md
│   │   ├── CANONICAL_TIMELINE_MODEL.md
│   │   ├── CANONICAL_VIDEO_CONTRACT.md
│   │   ├── CONTRACT_DEPENDENCY_RULES.md
│   │   ├── CREATIVEPLAN_TO_EDITABLE_DOCUMENT.md
│   │   ├── CURRENT_PREVIEW_FLOW.md
│   │   ├── CURRENT_RENDER_FLOW.md
│   │   ├── EDITOR_REVISION_MODEL.md
│   │   ├── ENGINE_NEUTRAL_TEMPLATE_ARCHITECTURE.md
│   │   ├── FRAME_EVALUATION_MODEL.md
│   │   ├── FUTURE_ARCHITECTURE_GUARDS.md
│   │   ├── INTERMEDIATE_ARTIFACT_MODEL.md
│   │   ├── KEYFRAME_ANIMATION_MODEL.md
│   │   ├── LAYER_MODEL.md
│   │   ├── MASTER_COMPOSITOR_ARCHITECTURE.md
│   │   ├── MULTI_ENGINE_EXECUTION.md
│   │   ├── MUTATION_INVALIDATION_MODEL.md
│   │   ├── OUTPUT_NORMALIZATION_MODEL.md
│   │   ├── PREVIEW_CACHE_INVALIDATION.md
│   │   ├── PREVIEW_FIDELITY_MODEL.md
│   │   ├── PREVIEW_PROXY_ARCHITECTURE.md
│   │   ├── R02_MIGRATION_MAP.md
│   │   ├── R03_COMPATIBILITY_MAP.md
│   │   ├── R04_COMPATIBILITY_MAP.md
│   │   ├── R07B_COMPATIBILITY_MAP.md
│   │   ├── R08_COMPATIBILITY_MAP.md
│   │   ├── R09_COMPATIBILITY_MAP.md
│   │   ├── R10_COMPATIBILITY_MAP.md
│   │   ├── R11_COMPATIBILITY_MAP.md
│   │   ├── R12_COMPATIBILITY_MAP.md
│   │   ├── R13_COMPATIBILITY_MAP.md
│   │   ├── REMOTION_COUPLING_INVENTORY.json
│   │   ├── REMOTION_LOCKIN_SCORECARD.md
│   │   ├── REMOTION_RENDERER_ADAPTER.md
│   │   ├── RENDER_EDITOR_DEPENDENCY_GRAPH.md
│   │   ├── RENDER_GRAPH_ARCHITECTURE.md
│   │   ├── RENDER_PLANNER_MODEL.md
│   │   ├── RENDER_PLANNING_POLICY.md
│   │   ├── RENDERER_ARCHITECTURE.md
│   │   ├── RENDERER_CAPABILITY_MODEL.md
│   │   ├── RENDERER_REGISTRY_MODEL.md
│   │   ├── S28-R14_ARCHITECTURE.md
│   │   ├── S28-R14_REPORT.md
│   │   ├── S28-R15_EVIDENCE_PART_1_2.md
│   │   ├── S28-R15_REPORT.md
│   │   ├── S28-R_ARCHITECTURE_BASELINE.md
│   │   ├── S28-R_FINAL_ARCHITECTURE.md
│   │   ├── S28-R_FINAL_REPORT.md
│   │   ├── TEMPLATE_INVENTORY_S28_R05.json
│   │   ├── TEMPLATE_RUNTIME_MATRIX.md
│   │   ├── TIMEBASE_AND_DURATION_SEMANTICS.md
│   │   ├── UNDO_REDO_MODEL.md
│   │   ├── UNIFIED_AUTHORING_ARCHITECTURE.md
│   │   └── WAVEFORM_MODEL.md
│   ├── tools/
│   │   ├── breakdown.py
│   │   ├── build_massive_report.py
│   │   ├── generate_overview.py
│   │   └── print_orphans.py
│   ├── DEVELOPER_GUIDE.md
│   ├── EFFECTS_STATUS.md
│   ├── LIBRARY_STATUS.md
│   ├── PLUGIN_ARCHITECTURE.md
│   ├── QUICK_START.md
│   ├── README.md
│   └── USER_GUIDE.md
├── ground-truth/
│   ├── collections/
│   │   ├── ads.md
│   │   ├── explainers.md
│   │   ├── product.md
│   │   ├── saas.md
│   │   └── social.md
│   ├── adapter_family_candidates.json
│   ├── ASSET_INDEX.json
│   ├── CANONICAL_PATHS.json
│   ├── CINEMATIC_INDEX.md
│   ├── MCP_INDEX.md
│   ├── orchestration_resolved_spec.json
│   ├── PLAYBOOKS_INDEX.md
│   ├── RECIPES_INDEX.md
│   ├── template_catalog.json
│   ├── TEMPLATE_DUPLICATES.md
│   ├── TEMPLATE_INDEX.md
│   ├── TOOLS_INDEX.md
│   └── VOCAB_REMAP.md
├── node_modules/  [مكتبات npm العامة مستثناة، مقتصر على مكتبات القوالب أدناه]
│   └── remotion-bits/
│       ├── dist/
│       │   ├── bin/
│       │   │   ├── remotion-bits.d.ts
│       │   │   └── remotion-bits.js
│       │   ├── catalog/
│       │   │   ├── contracts.d.ts
│       │   │   ├── contracts.js
│       │   │   ├── inventory.generated.d.ts
│       │   │   ├── inventory.generated.js
│       │   │   ├── runtime.d.ts
│       │   │   ├── runtime.js
│       │   │   ├── shared.d.ts
│       │   │   └── shared.js
│       │   ├── cli/
│       │   │   ├── remotion-bits.d.ts
│       │   │   └── remotion-bits.js
│       │   ├── components/
│       │   │   ├── ParticleSystem/
│       │   │   │   ├── Behavior.d.ts
│       │   │   │   ├── Behavior.js
│       │   │   │   ├── index.d.ts
│       │   │   │   ├── index.js
│       │   │   │   ├── Particles.d.ts
│       │   │   │   ├── Particles.js
│       │   │   │   ├── Spawner.d.ts
│       │   │   │   └── Spawner.js
│       │   │   ├── Scene3D/
│       │   │   │   ├── context.d.ts
│       │   │   │   ├── context.js
│       │   │   │   ├── Element3D.d.ts
│       │   │   │   ├── Element3D.js
│       │   │   │   ├── index.d.ts
│       │   │   │   ├── index.js
│       │   │   │   ├── Scene3D.d.ts
│       │   │   │   ├── Scene3D.js
│       │   │   │   ├── Step.d.ts
│       │   │   │   ├── Step.js
│       │   │   │   ├── StepResponsive.d.ts
│       │   │   │   ├── StepResponsive.js
│       │   │   │   ├── types.d.ts
│       │   │   │   └── types.js
│       │   │   ├── AnimatedCounter.d.ts
│       │   │   ├── AnimatedCounter.js
│       │   │   ├── AnimatedText.d.ts
│       │   │   ├── AnimatedText.js
│       │   │   ├── CodeBlock.d.ts
│       │   │   ├── CodeBlock.js
│       │   │   ├── GradientTransition.d.ts
│       │   │   ├── GradientTransition.js
│       │   │   ├── index.d.ts
│       │   │   ├── index.js
│       │   │   ├── MatrixRain.d.ts
│       │   │   ├── MatrixRain.js
│       │   │   ├── ScrollingImages.d.ts
│       │   │   ├── ScrollingImages.js
│       │   │   ├── StaggeredMotion.d.ts
│       │   │   ├── StaggeredMotion.js
│       │   │   ├── TypeWriter.d.ts
│       │   │   └── TypeWriter.js
│       │   ├── hooks/
│       │   │   ├── index.d.ts
│       │   │   ├── index.js
│       │   │   ├── useViewportRect.d.ts
│       │   │   └── useViewportRect.js
│       │   ├── mcp/
│       │   │   ├── remotion-bits.d.ts
│       │   │   └── remotion-bits.js
│       │   ├── utils/
│       │   │   ├── motion/
│       │   │   │   ├── index.d.ts
│       │   │   │   └── index.js
│       │   │   ├── particles/
│       │   │   │   ├── behaviors.d.ts
│       │   │   │   ├── behaviors.js
│       │   │   │   ├── index.d.ts
│       │   │   │   ├── index.js
│       │   │   │   ├── simulator.d.ts
│       │   │   │   ├── simulator.js
│       │   │   │   ├── types.d.ts
│       │   │   │   └── types.js
│       │   │   ├── color.d.ts
│       │   │   ├── color.js
│       │   │   ├── geometry.d.ts
│       │   │   ├── geometry.js
│       │   │   ├── gradient.d.ts
│       │   │   ├── gradient.js
│       │   │   ├── index.d.ts
│       │   │   ├── index.js
│       │   │   ├── interpolate.d.ts
│       │   │   ├── interpolate.js
│       │   │   ├── interpolate3d.d.ts
│       │   │   ├── interpolate3d.js
│       │   │   ├── random.d.ts
│       │   │   ├── random.js
│       │   │   ├── StepContext.d.ts
│       │   │   ├── StepContext.js
│       │   │   ├── transform3d.d.ts
│       │   │   └── transform3d.js
│       │   ├── bits.config.d.ts
│       │   ├── bits.config.js
│       │   ├── index.d.ts
│       │   └── index.js
│       ├── docs/
│       │   ├── src/
│       │   │   └── bits/
│       │   │       └── examples/
│       │   │           ├── animated-counter/
│       │   │           │   ├── BasicCounter.tsx
│       │   │           │   └── CounterConfetti.tsx
│       │   │           ├── animated-text/
│       │   │           │   ├── BlurSlideWord.tsx
│       │   │           │   ├── CharByChar.tsx
│       │   │           │   ├── FadeIn.tsx
│       │   │           │   ├── GlitchCycle.tsx
│       │   │           │   ├── GlitchIn.tsx
│       │   │           │   ├── MatrixRain.tsx
│       │   │           │   └── WordByWord.tsx
│       │   │           ├── code-block/
│       │   │           │   ├── BasicCodeBlock.tsx
│       │   │           │   └── TypingCodeBlock.tsx
│       │   │           ├── gradient-transition/
│       │   │           │   ├── ConicGradient.tsx
│       │   │           │   ├── LinearGradient.tsx
│       │   │           │   └── RadialGradient.tsx
│       │   │           ├── particle-system/
│       │   │           │   ├── Fireflies.tsx
│       │   │           │   ├── ParticlesFountain.tsx
│       │   │           │   ├── ParticlesGrid.tsx
│       │   │           │   ├── ParticlesSnow.tsx
│       │   │           │   └── ScrollingColumns.tsx
│       │   │           ├── scene-3d/
│       │   │           │   ├── 3DBasic.tsx
│       │   │           │   ├── 3DElements.tsx
│       │   │           │   ├── Carousel.tsx
│       │   │           │   ├── CubeNavigation.tsx
│       │   │           │   ├── CursorFlyover.tsx
│       │   │           │   ├── FlyingThroughWords.tsx
│       │   │           │   ├── KenBurns.tsx
│       │   │           │   ├── StepTimingContext.tsx
│       │   │           │   ├── Terminal3D.tsx
│       │   │           │   └── Transform3DShowcase.tsx
│       │   │           ├── showcase/
│       │   │           │   └── FeatureShowcase.tsx
│       │   │           ├── staggered-motion/
│       │   │           │   ├── CardStack.tsx
│       │   │           │   ├── EasingsVisualizer.tsx
│       │   │           │   ├── FractureReassemble.tsx
│       │   │           │   ├── GridStagger.tsx
│       │   │           │   ├── ListReveal.tsx
│       │   │           │   ├── MosaicReframe.tsx
│       │   │           │   ├── SlideFromLeft.tsx
│       │   │           │   └── StaggeredFadeIn.tsx
│       │   │           └── typewriter/
│       │   │               ├── BasicTypewriter.tsx
│       │   │               ├── CLISimulation.tsx
│       │   │               ├── MultiTextTypewriter.tsx
│       │   │               └── VariableSpeedTypewriter.tsx
│       │   └── README.md
│       ├── src/
│       │   ├── bin/
│       │   │   └── remotion-bits.ts
│       │   ├── catalog/
│       │   │   ├── __tests__/
│       │   │   │   └── runtime-catalog.test.ts
│       │   │   ├── contracts.ts
│       │   │   ├── inventory.generated.json
│       │   │   ├── inventory.generated.ts
│       │   │   ├── runtime.ts
│       │   │   └── shared.ts
│       │   ├── cli/
│       │   │   └── remotion-bits.ts
│       │   ├── components/
│       │   │   ├── __tests__/
│       │   │   │   ├── AnimatedCounter.test.tsx
│       │   │   │   ├── AnimatedText.test.tsx
│       │   │   │   ├── GradientTransition.test.tsx
│       │   │   │   ├── Scene3D.test.tsx
│       │   │   │   ├── StaggeredMotion.test.tsx
│       │   │   │   └── StepResponsive.test.tsx
│       │   │   ├── ParticleSystem/
│       │   │   │   ├── Behavior.tsx
│       │   │   │   ├── index.ts
│       │   │   │   ├── Particles.tsx
│       │   │   │   └── Spawner.tsx
│       │   │   ├── Scene3D/
│       │   │   │   ├── context.ts
│       │   │   │   ├── Element3D.tsx
│       │   │   │   ├── index.ts
│       │   │   │   ├── Scene3D.tsx
│       │   │   │   ├── Step.tsx
│       │   │   │   ├── StepResponsive.tsx
│       │   │   │   └── types.ts
│       │   │   ├── AnimatedCounter.tsx
│       │   │   ├── AnimatedText.tsx
│       │   │   ├── CodeBlock.tsx
│       │   │   ├── GradientTransition.tsx
│       │   │   ├── index.ts
│       │   │   ├── MatrixRain.tsx
│       │   │   ├── ScrollingImages.tsx
│       │   │   ├── StaggeredMotion.tsx
│       │   │   └── TypeWriter.tsx
│       │   ├── hooks/
│       │   │   ├── index.ts
│       │   │   └── useViewportRect.ts
│       │   ├── mcp/
│       │   │   └── remotion-bits.ts
│       │   ├── utils/
│       │   │   ├── __tests__/
│       │   │   │   ├── color.test.ts
│       │   │   │   ├── geometry3d.test.ts
│       │   │   │   ├── gradient.test.ts
│       │   │   │   ├── interpolate.test.ts
│       │   │   │   ├── interpolate3d.test.ts
│       │   │   │   ├── radial-position.test.ts
│       │   │   │   ├── random.test.ts
│       │   │   │   └── transform3d.test.ts
│       │   │   ├── motion/
│       │   │   │   └── index.ts
│       │   │   ├── particles/
│       │   │   │   ├── __tests__/
│       │   │   │   │   ├── behaviors-variance.test.ts
│       │   │   │   │   └── simulator.test.ts
│       │   │   │   ├── behaviors.ts
│       │   │   │   ├── index.ts
│       │   │   │   ├── simulator.ts
│       │   │   │   └── types.ts
│       │   │   ├── color.ts
│       │   │   ├── geometry.ts
│       │   │   ├── gradient.ts
│       │   │   ├── index.ts
│       │   │   ├── interpolate.ts
│       │   │   ├── interpolate3d.ts
│       │   │   ├── random.ts
│       │   │   ├── StepContext.ts
│       │   │   └── transform3d.ts
│       │   ├── bits.config.ts
│       │   ├── culori.d.ts
│       │   └── index.ts
│       ├── package.json
│       ├── README.md
│       └── registry.json
├── planner/
│   ├── cache-evaluator.ts
│   ├── cost-estimator.ts
│   ├── index.ts
│   ├── planning-policy.ts
│   ├── production-render-graph-executor.ts
│   ├── render-graph-executor.ts
│   └── render-planner.ts
├── preview/
│   ├── audio/
│   │   ├── audio-preview-runtime.ts
│   │   ├── audio-types.ts
│   │   ├── index.ts
│   │   ├── waveform-analyzer.ts
│   │   └── web-audio-adapter.ts
│   ├── components/
│   │   └── LivePreviewPlayer.tsx
│   ├── proxy/
│   │   ├── index.ts
│   │   ├── production-preview-coordinator.ts
│   │   ├── proxy-cache.ts
│   │   └── proxy-coordinator.ts
│   ├── capabilities.ts
│   ├── dom-driver.ts
│   ├── index.ts
│   ├── preview-runtime.ts
│   ├── types.ts
│   └── visual-frame.ts
├── projects/  [مجلد المشاريع التجريبية - مستثنى مئات مجلدات prj_* و test-*]
├── public/
│   └── media/  [مجلد وسائط مستثناة أو فارغ]
├── recipes/
│   ├── agent-browser-proof.json
│   ├── avatar-explainer.json
│   ├── avatar-hook-broll.json
│   ├── avatar-insta-split.json
│   ├── avatar-product-walkthrough.json
│   ├── avatar-vo-broll.json
│   ├── captioned-talking-head.json
│   ├── dynamic-montage-ad.json
│   ├── faceless-broll-ad.json
│   ├── living-canvas-explainer.json
│   ├── longform-repurpose.json
│   ├── misotts-article-sprint.json
│   ├── motion-collage-explainer.json
│   ├── motion-graphics.json
│   ├── README.md
│   ├── review-conquest-compilation.json
│   ├── schema.json
│   ├── screencast-demo.json
│   ├── tabletop-levels-explainer.json
│   └── ugc-ai-ad.json
├── references/
│   ├── 1_playbooks/
│   │   ├── ffmpeg_recipes.md
│   │   ├── hook_playbook_article_sprint.md
│   │   ├── living_canvas.md
│   │   ├── motion_collage.md
│   │   ├── review_video.md
│   │   ├── tabletop_explainer.md
│   │   └── video_copy.md
│   ├── 2_sops/
│   │   ├── hyperrealistic_image.md
│   │   ├── plan_template.md
│   │   ├── seedance_avatar.md
│   │   ├── spoken_vo_humanizer.md
│   │   └── template_proposal.md
│   ├── 3_engineering/
│   │   └── remotion_guide.md
│   ├── 4_taste_engine/
│   │   ├── choreography.md
│   │   ├── context-adaptation.md
│   │   ├── core-philosophy.md
│   │   ├── decision-framework.md
│   │   ├── disney-principles.md
│   │   ├── emotion-mapping.md
│   │   ├── motion-personality.md
│   │   ├── narrative-structure.md
│   │   ├── sfx_binding_matrix.md
│   │   └── user-signature-style.md
│   ├── README.md
│   └── ROUTER.md
├── registry/
│   ├── thumbs/
│   │   └── .gitkeep
│   ├── auto-generated-entries.ts
│   ├── docs-extractor.ts
│   ├── docs-worklist.json
│   ├── effects-catalog.ts
│   ├── effects-runtime.ts
│   ├── engine-classification.json
│   ├── ids.json
│   ├── README.md
│   ├── semantic-registry.ts
│   ├── template-aliases.ts
│   ├── template-migration-manifest.json
│   ├── template-registry-data.json
│   ├── template-registry.tsx
│   ├── template-specs-data.json
│   ├── tier-map.json
│   └── types.ts
├── remotion/
│   ├── index.ts
│   └── remotion-renderer-adapter.ts
├── remotion-app/
│   ├── node_modules/  [مكتبات npm العامة مستثناة، مقتصر على مكتبات القوالب أدناه]
│   │   ├── remotion-bits/
│   │   │   ├── dist/
│   │   │   │   ├── bin/
│   │   │   │   │   ├── remotion-bits.d.ts
│   │   │   │   │   └── remotion-bits.js
│   │   │   │   ├── catalog/
│   │   │   │   │   ├── contracts.d.ts
│   │   │   │   │   ├── contracts.js
│   │   │   │   │   ├── inventory.generated.d.ts
│   │   │   │   │   ├── inventory.generated.js
│   │   │   │   │   ├── runtime.d.ts
│   │   │   │   │   ├── runtime.js
│   │   │   │   │   ├── shared.d.ts
│   │   │   │   │   └── shared.js
│   │   │   │   ├── cli/
│   │   │   │   │   ├── remotion-bits.d.ts
│   │   │   │   │   └── remotion-bits.js
│   │   │   │   ├── components/
│   │   │   │   │   ├── ParticleSystem/
│   │   │   │   │   │   ├── Behavior.d.ts
│   │   │   │   │   │   ├── Behavior.js
│   │   │   │   │   │   ├── index.d.ts
│   │   │   │   │   │   ├── index.js
│   │   │   │   │   │   ├── Particles.d.ts
│   │   │   │   │   │   ├── Particles.js
│   │   │   │   │   │   ├── Spawner.d.ts
│   │   │   │   │   │   └── Spawner.js
│   │   │   │   │   ├── Scene3D/
│   │   │   │   │   │   ├── context.d.ts
│   │   │   │   │   │   ├── context.js
│   │   │   │   │   │   ├── Element3D.d.ts
│   │   │   │   │   │   ├── Element3D.js
│   │   │   │   │   │   ├── index.d.ts
│   │   │   │   │   │   ├── index.js
│   │   │   │   │   │   ├── Scene3D.d.ts
│   │   │   │   │   │   ├── Scene3D.js
│   │   │   │   │   │   ├── Step.d.ts
│   │   │   │   │   │   ├── Step.js
│   │   │   │   │   │   ├── StepResponsive.d.ts
│   │   │   │   │   │   ├── StepResponsive.js
│   │   │   │   │   │   ├── types.d.ts
│   │   │   │   │   │   └── types.js
│   │   │   │   │   ├── AnimatedCounter.d.ts
│   │   │   │   │   ├── AnimatedCounter.js
│   │   │   │   │   ├── AnimatedText.d.ts
│   │   │   │   │   ├── AnimatedText.js
│   │   │   │   │   ├── CodeBlock.d.ts
│   │   │   │   │   ├── CodeBlock.js
│   │   │   │   │   ├── GradientTransition.d.ts
│   │   │   │   │   ├── GradientTransition.js
│   │   │   │   │   ├── index.d.ts
│   │   │   │   │   ├── index.js
│   │   │   │   │   ├── MatrixRain.d.ts
│   │   │   │   │   ├── MatrixRain.js
│   │   │   │   │   ├── ScrollingImages.d.ts
│   │   │   │   │   ├── ScrollingImages.js
│   │   │   │   │   ├── StaggeredMotion.d.ts
│   │   │   │   │   ├── StaggeredMotion.js
│   │   │   │   │   ├── TypeWriter.d.ts
│   │   │   │   │   └── TypeWriter.js
│   │   │   │   ├── hooks/
│   │   │   │   │   ├── index.d.ts
│   │   │   │   │   ├── index.js
│   │   │   │   │   ├── useViewportRect.d.ts
│   │   │   │   │   └── useViewportRect.js
│   │   │   │   ├── mcp/
│   │   │   │   │   ├── remotion-bits.d.ts
│   │   │   │   │   └── remotion-bits.js
│   │   │   │   ├── utils/
│   │   │   │   │   ├── motion/
│   │   │   │   │   │   ├── index.d.ts
│   │   │   │   │   │   └── index.js
│   │   │   │   │   ├── particles/
│   │   │   │   │   │   ├── behaviors.d.ts
│   │   │   │   │   │   ├── behaviors.js
│   │   │   │   │   │   ├── index.d.ts
│   │   │   │   │   │   ├── index.js
│   │   │   │   │   │   ├── simulator.d.ts
│   │   │   │   │   │   ├── simulator.js
│   │   │   │   │   │   ├── types.d.ts
│   │   │   │   │   │   └── types.js
│   │   │   │   │   ├── color.d.ts
│   │   │   │   │   ├── color.js
│   │   │   │   │   ├── geometry.d.ts
│   │   │   │   │   ├── geometry.js
│   │   │   │   │   ├── gradient.d.ts
│   │   │   │   │   ├── gradient.js
│   │   │   │   │   ├── index.d.ts
│   │   │   │   │   ├── index.js
│   │   │   │   │   ├── interpolate.d.ts
│   │   │   │   │   ├── interpolate.js
│   │   │   │   │   ├── interpolate3d.d.ts
│   │   │   │   │   ├── interpolate3d.js
│   │   │   │   │   ├── random.d.ts
│   │   │   │   │   ├── random.js
│   │   │   │   │   ├── StepContext.d.ts
│   │   │   │   │   ├── StepContext.js
│   │   │   │   │   ├── transform3d.d.ts
│   │   │   │   │   └── transform3d.js
│   │   │   │   ├── bits.config.d.ts
│   │   │   │   ├── bits.config.js
│   │   │   │   ├── index.d.ts
│   │   │   │   └── index.js
│   │   │   ├── docs/
│   │   │   │   ├── src/
│   │   │   │   │   └── bits/
│   │   │   │   │       └── examples/
│   │   │   │   │           ├── animated-counter/
│   │   │   │   │           │   ├── BasicCounter.tsx
│   │   │   │   │           │   └── CounterConfetti.tsx
│   │   │   │   │           ├── animated-text/
│   │   │   │   │           │   ├── BlurSlideWord.tsx
│   │   │   │   │           │   ├── CharByChar.tsx
│   │   │   │   │           │   ├── FadeIn.tsx
│   │   │   │   │           │   ├── GlitchCycle.tsx
│   │   │   │   │           │   ├── GlitchIn.tsx
│   │   │   │   │           │   ├── MatrixRain.tsx
│   │   │   │   │           │   └── WordByWord.tsx
│   │   │   │   │           ├── code-block/
│   │   │   │   │           │   ├── BasicCodeBlock.tsx
│   │   │   │   │           │   └── TypingCodeBlock.tsx
│   │   │   │   │           ├── gradient-transition/
│   │   │   │   │           │   ├── ConicGradient.tsx
│   │   │   │   │           │   ├── LinearGradient.tsx
│   │   │   │   │           │   └── RadialGradient.tsx
│   │   │   │   │           ├── particle-system/
│   │   │   │   │           │   ├── Fireflies.tsx
│   │   │   │   │           │   ├── ParticlesFountain.tsx
│   │   │   │   │           │   ├── ParticlesGrid.tsx
│   │   │   │   │           │   ├── ParticlesSnow.tsx
│   │   │   │   │           │   └── ScrollingColumns.tsx
│   │   │   │   │           ├── scene-3d/
│   │   │   │   │           │   ├── 3DBasic.tsx
│   │   │   │   │           │   ├── 3DElements.tsx
│   │   │   │   │           │   ├── Carousel.tsx
│   │   │   │   │           │   ├── CubeNavigation.tsx
│   │   │   │   │           │   ├── CursorFlyover.tsx
│   │   │   │   │           │   ├── FlyingThroughWords.tsx
│   │   │   │   │           │   ├── KenBurns.tsx
│   │   │   │   │           │   ├── StepTimingContext.tsx
│   │   │   │   │           │   ├── Terminal3D.tsx
│   │   │   │   │           │   └── Transform3DShowcase.tsx
│   │   │   │   │           ├── showcase/
│   │   │   │   │           │   └── FeatureShowcase.tsx
│   │   │   │   │           ├── staggered-motion/
│   │   │   │   │           │   ├── CardStack.tsx
│   │   │   │   │           │   ├── EasingsVisualizer.tsx
│   │   │   │   │           │   ├── FractureReassemble.tsx
│   │   │   │   │           │   ├── GridStagger.tsx
│   │   │   │   │           │   ├── ListReveal.tsx
│   │   │   │   │           │   ├── MosaicReframe.tsx
│   │   │   │   │           │   ├── SlideFromLeft.tsx
│   │   │   │   │           │   └── StaggeredFadeIn.tsx
│   │   │   │   │           └── typewriter/
│   │   │   │   │               ├── BasicTypewriter.tsx
│   │   │   │   │               ├── CLISimulation.tsx
│   │   │   │   │               ├── MultiTextTypewriter.tsx
│   │   │   │   │               └── VariableSpeedTypewriter.tsx
│   │   │   │   └── README.md
│   │   │   ├── src/
│   │   │   │   ├── bin/
│   │   │   │   │   └── remotion-bits.ts
│   │   │   │   ├── catalog/
│   │   │   │   │   ├── __tests__/
│   │   │   │   │   │   └── runtime-catalog.test.ts
│   │   │   │   │   ├── contracts.ts
│   │   │   │   │   ├── inventory.generated.json
│   │   │   │   │   ├── inventory.generated.ts
│   │   │   │   │   ├── runtime.ts
│   │   │   │   │   └── shared.ts
│   │   │   │   ├── cli/
│   │   │   │   │   └── remotion-bits.ts
│   │   │   │   ├── components/
│   │   │   │   │   ├── __tests__/
│   │   │   │   │   │   ├── AnimatedCounter.test.tsx
│   │   │   │   │   │   ├── AnimatedText.test.tsx
│   │   │   │   │   │   ├── GradientTransition.test.tsx
│   │   │   │   │   │   ├── Scene3D.test.tsx
│   │   │   │   │   │   ├── StaggeredMotion.test.tsx
│   │   │   │   │   │   └── StepResponsive.test.tsx
│   │   │   │   │   ├── ParticleSystem/
│   │   │   │   │   │   ├── Behavior.tsx
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   ├── Particles.tsx
│   │   │   │   │   │   └── Spawner.tsx
│   │   │   │   │   ├── Scene3D/
│   │   │   │   │   │   ├── context.ts
│   │   │   │   │   │   ├── Element3D.tsx
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   ├── Scene3D.tsx
│   │   │   │   │   │   ├── Step.tsx
│   │   │   │   │   │   ├── StepResponsive.tsx
│   │   │   │   │   │   └── types.ts
│   │   │   │   │   ├── AnimatedCounter.tsx
│   │   │   │   │   ├── AnimatedText.tsx
│   │   │   │   │   ├── CodeBlock.tsx
│   │   │   │   │   ├── GradientTransition.tsx
│   │   │   │   │   ├── index.ts
│   │   │   │   │   ├── MatrixRain.tsx
│   │   │   │   │   ├── ScrollingImages.tsx
│   │   │   │   │   ├── StaggeredMotion.tsx
│   │   │   │   │   └── TypeWriter.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   ├── index.ts
│   │   │   │   │   └── useViewportRect.ts
│   │   │   │   ├── mcp/
│   │   │   │   │   └── remotion-bits.ts
│   │   │   │   ├── utils/
│   │   │   │   │   ├── __tests__/
│   │   │   │   │   │   ├── color.test.ts
│   │   │   │   │   │   ├── geometry3d.test.ts
│   │   │   │   │   │   ├── gradient.test.ts
│   │   │   │   │   │   ├── interpolate.test.ts
│   │   │   │   │   │   ├── interpolate3d.test.ts
│   │   │   │   │   │   ├── radial-position.test.ts
│   │   │   │   │   │   ├── random.test.ts
│   │   │   │   │   │   └── transform3d.test.ts
│   │   │   │   │   ├── motion/
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── particles/
│   │   │   │   │   │   ├── __tests__/
│   │   │   │   │   │   │   ├── behaviors-variance.test.ts
│   │   │   │   │   │   │   └── simulator.test.ts
│   │   │   │   │   │   ├── behaviors.ts
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   ├── simulator.ts
│   │   │   │   │   │   └── types.ts
│   │   │   │   │   ├── color.ts
│   │   │   │   │   ├── geometry.ts
│   │   │   │   │   ├── gradient.ts
│   │   │   │   │   ├── index.ts
│   │   │   │   │   ├── interpolate.ts
│   │   │   │   │   ├── interpolate3d.ts
│   │   │   │   │   ├── random.ts
│   │   │   │   │   ├── StepContext.ts
│   │   │   │   │   └── transform3d.ts
│   │   │   │   ├── bits.config.ts
│   │   │   │   ├── culori.d.ts
│   │   │   │   └── index.ts
│   │   │   ├── package.json
│   │   │   ├── README.md
│   │   │   └── registry.json
│   │   └── remotion-ui/
│   │       ├── dist/
│   │       │   ├── registry/
│   │       │   │   ├── index.d.ts
│   │       │   │   └── index.js
│   │       │   ├── schema/
│   │       │   │   ├── index.d.ts
│   │       │   │   └── index.js
│   │       │   ├── index.d.ts
│   │       │   └── index.js
│   │       ├── templates/
│   │       │   ├── agent-skill/
│   │       │   │   └── SKILL.md
│   │       │   └── remotion-app/
│   │       │       ├── src/
│   │       │       │   ├── compositions/
│   │       │       │   │   └── welcome/
│   │       │       │   │       └── index.tsx
│   │       │       │   ├── remotion/
│   │       │       │   │   ├── lib/
│   │       │       │   │   │   └── .gitkeep
│   │       │       │   │   ├── primitives/
│   │       │       │   │   │   └── .gitkeep
│   │       │       │   │   └── scenes/
│   │       │       │   │       └── .gitkeep
│   │       │       │   ├── index.ts
│   │       │       │   └── Root.tsx
│   │       │       ├── package.json
│   │       │       ├── remotion-ui.json
│   │       │       ├── remotion.config.ts
│   │       │       └── tsconfig.json
│   │       ├── package.json
│   │       └── README.md
│   ├── out/  [مجلد وسائط مستثناة أو فارغ]
│   ├── projects/  [مجلد المشاريع التجريبية - مستثنى مئات مجلدات prj_* و test-*]
│   ├── public/
│   │   ├── media/
│   │   │   ├── audio/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   ├── icons/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   └── sfx/  [مجلد وسائط مستثناة أو فارغ]
│   │   └── render-props.json
│   ├── src/
│   │   ├── __tests__/
│   │   │   └── merge.test.ts
│   │   ├── compositions/
│   │   │   ├── ai-composer-showcase/
│   │   │   │   └── index.tsx
│   │   │   ├── ai-generation-canvas/
│   │   │   │   └── index.tsx
│   │   │   ├── bento-pan/
│   │   │   │   └── index.tsx
│   │   │   ├── browser-flow/
│   │   │   │   └── index.tsx
│   │   │   ├── creator-reel/
│   │   │   │   └── index.tsx
│   │   │   ├── dashboard-populate/
│   │   │   │   └── index.tsx
│   │   │   ├── data-story/
│   │   │   │   └── index.tsx
│   │   │   ├── deploy-reveal/
│   │   │   │   └── index.tsx
│   │   │   ├── ecosystem-orbit/
│   │   │   │   └── index.tsx
│   │   │   ├── hero-device-assemble/
│   │   │   │   └── index.tsx
│   │   │   ├── hero-loop/
│   │   │   │   └── index.tsx
│   │   │   ├── image-expand/
│   │   │   │   └── index.tsx
│   │   │   ├── intro/
│   │   │   │   └── index.tsx
│   │   │   ├── landing-code-showcase/
│   │   │   │   └── index.tsx
│   │   │   ├── live-code-split/
│   │   │   │   └── index.tsx
│   │   │   ├── podcast-clip/
│   │   │   │   └── index.tsx
│   │   │   ├── pricing-focus/
│   │   │   │   └── index.tsx
│   │   │   ├── showcase/
│   │   │   │   └── index.tsx
│   │   │   ├── social-clip/
│   │   │   │   └── index.tsx
│   │   │   ├── tool-menu-slide/
│   │   │   │   └── index.tsx
│   │   │   └── tutorial-clip/
│   │   │       └── index.tsx
│   │   ├── engine/
│   │   │   ├── audio/
│   │   │   │   ├── AudioManager.tsx
│   │   │   │   ├── index.ts
│   │   │   │   ├── resolveCues.ts
│   │   │   │   └── types.ts
│   │   │   ├── camera/
│   │   │   │   ├── AutoZoom.tsx
│   │   │   │   ├── CameraRig.tsx
│   │   │   │   ├── index.ts
│   │   │   │   ├── interpolate.ts
│   │   │   │   ├── resolveTimeline.ts
│   │   │   │   └── types.ts
│   │   │   ├── choreography/
│   │   │   │   ├── filterCursorPath.ts
│   │   │   │   ├── index.ts
│   │   │   │   ├── mapCursorPath.ts
│   │   │   │   └── resolveWindowPose.ts
│   │   │   ├── cursor/
│   │   │   │   ├── arc.ts
│   │   │   │   ├── Cursor.tsx
│   │   │   │   ├── CursorSprite.tsx
│   │   │   │   ├── index.ts
│   │   │   │   ├── resolveAnchor.ts
│   │   │   │   └── types.ts
│   │   │   ├── layout/
│   │   │   │   ├── index.ts
│   │   │   │   ├── LayoutContext.tsx
│   │   │   │   ├── LayoutWindow.tsx
│   │   │   │   ├── types.ts
│   │   │   │   ├── useWindowRect.ts
│   │   │   │   └── zones.ts
│   │   │   ├── primitives/
│   │   │   │   ├── app-ui/
│   │   │   │   │   ├── AppFromDescriptor.tsx
│   │   │   │   │   ├── AppShell.tsx
│   │   │   │   │   ├── Avatar.tsx
│   │   │   │   │   ├── Badge.tsx
│   │   │   │   │   ├── Button.tsx
│   │   │   │   │   ├── DataTable.tsx
│   │   │   │   │   ├── index.ts
│   │   │   │   │   ├── ListItems.tsx
│   │   │   │   │   ├── MessageList.tsx
│   │   │   │   │   ├── NotificationToast.tsx
│   │   │   │   │   ├── Panel.tsx
│   │   │   │   │   ├── PanelGrid.tsx
│   │   │   │   │   ├── Placeholder.tsx
│   │   │   │   │   ├── SearchBar.tsx
│   │   │   │   │   ├── SidebarNav.tsx
│   │   │   │   │   ├── StatCard.tsx
│   │   │   │   │   ├── TabBar.tsx
│   │   │   │   │   └── TopNav.tsx
│   │   │   │   ├── CountUp.tsx
│   │   │   │   ├── EndCard.tsx
│   │   │   │   ├── Enter.tsx
│   │   │   │   ├── Exit.tsx
│   │   │   │   ├── Headline.tsx
│   │   │   │   ├── Highlight.tsx
│   │   │   │   ├── index.ts
│   │   │   │   ├── Pulse.tsx
│   │   │   │   ├── ScenePush.tsx
│   │   │   │   ├── Stagger.tsx
│   │   │   │   ├── TrafficLights.tsx
│   │   │   │   ├── TypeWriter.tsx
│   │   │   │   ├── Wallpaper.tsx
│   │   │   │   └── Window.tsx
│   │   │   ├── scenes/
│   │   │   │   ├── ChaosDesktop.tsx
│   │   │   │   ├── Closer.tsx
│   │   │   │   ├── DynamicWindows.tsx
│   │   │   │   ├── FeatureShowcase.tsx
│   │   │   │   ├── HeadlineResolution.tsx
│   │   │   │   ├── index.ts
│   │   │   │   └── ProductReveal.tsx
│   │   │   ├── ui-state/
│   │   │   │   ├── generatePressKeyframes.ts
│   │   │   │   ├── index.ts
│   │   │   │   ├── types.ts
│   │   │   │   └── UIStateProvider.tsx
│   │   │   ├── fonts.ts
│   │   │   ├── index.ts
│   │   │   ├── schema.ts
│   │   │   ├── tokens.ts
│   │   │   └── types.ts
│   │   ├── lib/
│   │   │   ├── onda/
│   │   │   │   ├── primitives/
│   │   │   │   │   ├── Camera.tsx
│   │   │   │   │   ├── Glow.tsx
│   │   │   │   │   ├── GridField.tsx
│   │   │   │   │   ├── index.ts
│   │   │   │   │   └── Surface.tsx
│   │   │   │   ├── canvas-schemas.ts
│   │   │   │   ├── canvas.tsx
│   │   │   │   ├── choreography.ts
│   │   │   │   ├── easing.ts
│   │   │   │   ├── elevation.ts
│   │   │   │   ├── hooks.ts
│   │   │   │   ├── motion.ts
│   │   │   │   ├── random.ts
│   │   │   │   ├── timing.ts
│   │   │   │   └── tokens.ts
│   │   │   ├── remocn-ui/
│   │   │   │   ├── color.ts
│   │   │   │   ├── index.ts
│   │   │   │   ├── motion.ts
│   │   │   │   ├── theme.ts
│   │   │   │   ├── timeline.ts
│   │   │   │   └── types.ts
│   │   │   └── snap-cn-ui/
│   │   │       ├── color.ts
│   │   │       ├── fonts.ts
│   │   │       ├── index.ts
│   │   │       ├── motion.ts
│   │   │       ├── theme.ts
│   │   │       ├── timeline.ts
│   │   │       └── types.ts
│   │   ├── remotion/
│   │   │   ├── hooks/
│   │   │   │   └── use-stagger.ts
│   │   │   ├── lib/
│   │   │   │   ├── ai-composer-utils.tsx
│   │   │   │   ├── audio-viz-utils.ts
│   │   │   │   ├── caption-utils.ts
│   │   │   │   ├── chart-utils.ts
│   │   │   │   ├── code-syntax.tsx
│   │   │   │   ├── displacement-presentation.tsx
│   │   │   │   ├── displacement-transition.ts
│   │   │   │   ├── gpu.ts
│   │   │   │   ├── layout.ts
│   │   │   │   ├── map-utils.ts
│   │   │   │   ├── media-utils.ts
│   │   │   │   ├── motion-primitive.ts
│   │   │   │   ├── motion-tokens.ts
│   │   │   │   ├── motion-wrapper.tsx
│   │   │   │   ├── path-morph.ts
│   │   │   │   ├── path-utils.ts
│   │   │   │   ├── sample-media.ts
│   │   │   │   ├── springs.ts
│   │   │   │   ├── text-emphasis.ts
│   │   │   │   ├── text-fit-utils.ts
│   │   │   │   ├── text-split.ts
│   │   │   │   ├── timing.ts
│   │   │   │   └── transition-timing.ts
│   │   │   ├── primitives/
│   │   │   │   ├── audio-pulse.tsx
│   │   │   │   ├── audiogram-bars.tsx
│   │   │   │   ├── caption-highlight.tsx
│   │   │   │   ├── counter.tsx
│   │   │   │   ├── directional-wipe.tsx
│   │   │   │   ├── fade-in.tsx
│   │   │   │   ├── fade-out.tsx
│   │   │   │   ├── karaoke-captions.tsx
│   │   │   │   ├── line-chart-draw.tsx
│   │   │   │   ├── map-markers.tsx
│   │   │   │   ├── map-route.tsx
│   │   │   │   ├── multi-device-lineup.tsx
│   │   │   │   ├── path-draw.tsx
│   │   │   │   ├── slide-up.tsx
│   │   │   │   ├── spring-in.tsx
│   │   │   │   ├── stagger-children.tsx
│   │   │   │   ├── transition-fade.tsx
│   │   │   │   ├── transition-slide.tsx
│   │   │   │   ├── transition-wipe.tsx
│   │   │   │   ├── typewriter.tsx
│   │   │   │   └── waveform-line.tsx
│   │   │   └── scenes/
│   │   │       ├── animated-bar-chart/
│   │   │       │   └── index.tsx
│   │   │       ├── audiogram-scene/
│   │   │       │   └── index.tsx
│   │   │       ├── auto-fit-title/
│   │   │       │   └── index.tsx
│   │   │       ├── b-roll-stack/
│   │   │       │   └── index.tsx
│   │   │       ├── calendar-month-fill/
│   │   │       │   └── index.tsx
│   │   │       ├── callout-spotlight/
│   │   │       │   └── index.tsx
│   │   │       ├── caption-bumper/
│   │   │       │   └── index.tsx
│   │   │       ├── caption-scene/
│   │   │       │   └── index.tsx
│   │   │       ├── changelog-entry/
│   │   │       │   └── index.tsx
│   │   │       ├── chat-gpt/
│   │   │       │   └── index.tsx
│   │   │       ├── chat-to-preview/
│   │   │       │   └── index.tsx
│   │   │       ├── claude-chat/
│   │   │       │   └── index.tsx
│   │   │       ├── claude-code/
│   │   │       │   └── index.tsx
│   │   │       ├── code-accordion/
│   │   │       │   └── index.tsx
│   │   │       ├── code-diff-wipe/
│   │   │       │   └── index.tsx
│   │   │       ├── code-reveal/
│   │   │       │   └── index.tsx
│   │   │       ├── comment-callout/
│   │   │       │   └── index.tsx
│   │   │       ├── commit-graph/
│   │   │       │   └── index.tsx
│   │   │       ├── comparison-table/
│   │   │       │   └── index.tsx
│   │   │       ├── countdown-timer/
│   │   │       │   └── index.tsx
│   │   │       ├── data-flow-pipes/
│   │   │       │   └── index.tsx
│   │   │       ├── device-mockup-zoom/
│   │   │       │   └── index.tsx
│   │   │       ├── drag-drop-flow/
│   │   │       │   └── index.tsx
│   │   │       ├── end-card/
│   │   │       │   └── index.tsx
│   │   │       ├── faq-accordion/
│   │   │       │   └── index.tsx
│   │   │       ├── feature-list/
│   │   │       │   └── index.tsx
│   │   │       ├── file-tree-reveal/
│   │   │       │   └── index.tsx
│   │   │       ├── form-fill-sequence/
│   │   │       │   └── index.tsx
│   │   │       ├── hook-card/
│   │   │       │   └── index.tsx
│   │   │       ├── kanban-move/
│   │   │       │   └── index.tsx
│   │   │       ├── logo-reveal/
│   │   │       │   └── index.tsx
│   │   │       ├── logo-wall/
│   │   │       │   └── index.tsx
│   │   │       ├── lower-third/
│   │   │       │   └── index.tsx
│   │   │       ├── map-flight/
│   │   │       │   └── index.tsx
│   │   │       ├── media-frame/
│   │   │       │   └── index.tsx
│   │   │       ├── media-sequence/
│   │   │       │   └── index.tsx
│   │   │       ├── metric-ticker/
│   │   │       │   └── index.tsx
│   │   │       ├── news-ticker-bar/
│   │   │       │   └── index.tsx
│   │   │       ├── notification-stack/
│   │   │       │   └── index.tsx
│   │   │       ├── opencode/
│   │   │       │   └── index.tsx
│   │   │       ├── org-chart-build/
│   │   │       │   └── index.tsx
│   │   │       ├── poll-overlay/
│   │   │       │   └── index.tsx
│   │   │       ├── pricing-card/
│   │   │       │   └── index.tsx
│   │   │       ├── quiz-question/
│   │   │       │   └── index.tsx
│   │   │       ├── quote-card/
│   │   │       │   └── index.tsx
│   │   │       ├── reaction-burst/
│   │   │       │   └── index.tsx
│   │   │       ├── roadmap-lanes/
│   │   │       │   └── index.tsx
│   │   │       ├── search-results-populate/
│   │   │       │   └── index.tsx
│   │   │       ├── split-screen/
│   │   │       │   └── index.tsx
│   │   │       ├── sports-scorebug/
│   │   │       │   └── index.tsx
│   │   │       ├── stat-card/
│   │   │       │   └── index.tsx
│   │   │       ├── tab-switch-panel/
│   │   │       │   └── index.tsx
│   │   │       ├── talking-head-layout/
│   │   │       │   └── index.tsx
│   │   │       ├── team-grid/
│   │   │       │   └── index.tsx
│   │   │       ├── terminal-simulator/
│   │   │       │   └── index.tsx
│   │   │       ├── timeline-steps/
│   │   │       │   └── index.tsx
│   │   │       ├── title-card/
│   │   │       │   └── index.tsx
│   │   │       ├── v0/
│   │   │       │   └── index.tsx
│   │   │       ├── weather-card/
│   │   │       │   └── index.tsx
│   │   │       └── zoom-pan-frame/
│   │   │           └── index.tsx
│   │   ├── templates/
│   │   │   ├── custom/
│   │   │   │   ├── LevelOneScene.tsx
│   │   │   │   └── LevelZeroBox.tsx
│   │   │   ├── effects/
│   │   │   │   ├── BookFlipTransition.tsx
│   │   │   │   ├── ClockWipeTransition.tsx
│   │   │   │   ├── CrosswarpTransition.tsx
│   │   │   │   ├── CrossZoomTransition.tsx
│   │   │   │   ├── DissolveTransition.tsx
│   │   │   │   ├── DreamyZoomTransition.tsx
│   │   │   │   ├── engine-bridge.tsx
│   │   │   │   ├── FadeTransition.tsx
│   │   │   │   ├── FilmBurnTransition.tsx
│   │   │   │   ├── FlipTransition.tsx
│   │   │   │   ├── IrisTransition.tsx
│   │   │   │   ├── LinearBlurTransition.tsx
│   │   │   │   ├── PushCutTransition.tsx
│   │   │   │   ├── RippleTransition.tsx
│   │   │   │   ├── SlideTransition.tsx
│   │   │   │   ├── SwapTransition.tsx
│   │   │   │   ├── WipeTransition.tsx
│   │   │   │   ├── ZoomBlurTransition.tsx
│   │   │   │   └── ZoomInOutTransition.tsx
│   │   │   ├── elements/
│   │   │   │   ├── AnimatedBarChartWrapper.tsx
│   │   │   │   ├── AnimatedCounterWrapper.tsx
│   │   │   │   ├── AnimatedTextWrapper.tsx
│   │   │   │   ├── AutoFitTitleWrapper.tsx
│   │   │   │   ├── BentoPanWrapper.tsx
│   │   │   │   ├── BRollStackWrapper.tsx
│   │   │   │   ├── CalendarMonthFillWrapper.tsx
│   │   │   │   ├── CalloutSpotlightWrapper.tsx
│   │   │   │   ├── CaptionBumperWrapper.tsx
│   │   │   │   ├── ChangelogEntryWrapper.tsx
│   │   │   │   ├── ChatToPreviewWrapper.tsx
│   │   │   │   ├── CodeAccordionWrapper.tsx
│   │   │   │   ├── CodeBlockWrapper.tsx
│   │   │   │   ├── CodeDiffWipeWrapper.tsx
│   │   │   │   ├── CodeRevealWrapper.tsx
│   │   │   │   ├── CommentCalloutWrapper.tsx
│   │   │   │   ├── CommitGraphWrapper.tsx
│   │   │   │   ├── ComparisonTableWrapper.tsx
│   │   │   │   ├── CountdownTimerWrapper.tsx
│   │   │   │   ├── DashboardPopulateWrapper.tsx
│   │   │   │   ├── DeployRevealWrapper.tsx
│   │   │   │   ├── DeviceMockupZoomWrapper.tsx
│   │   │   │   ├── EndCardWrapper.tsx
│   │   │   │   ├── FaqAccordionWrapper.tsx
│   │   │   │   ├── FeatureListWrapper.tsx
│   │   │   │   ├── FileTreeRevealWrapper.tsx
│   │   │   │   ├── GradientWrapper.tsx
│   │   │   │   ├── HookCardWrapper.tsx
│   │   │   │   ├── ImageExpandWrapper.tsx
│   │   │   │   ├── KanbanMoveWrapper.tsx
│   │   │   │   ├── LogoRevealWrapper.tsx
│   │   │   │   ├── LogoWallWrapper.tsx
│   │   │   │   ├── LowerThirdWrapper.tsx
│   │   │   │   ├── MapFlightWrapper.tsx
│   │   │   │   ├── MatrixRainWrapper.tsx
│   │   │   │   ├── MediaFrameWrapper.tsx
│   │   │   │   ├── MetricTickerWrapper.tsx
│   │   │   │   ├── NewsTickerBarWrapper.tsx
│   │   │   │   ├── NotificationStackWrapper.tsx
│   │   │   │   ├── OrgChartBuildWrapper.tsx
│   │   │   │   ├── ParticleSystemWrapper.tsx
│   │   │   │   ├── PodcastClipWrapper.tsx
│   │   │   │   ├── PollOverlayWrapper.tsx
│   │   │   │   ├── PricingCardWrapper.tsx
│   │   │   │   ├── PricingFocusWrapper.tsx
│   │   │   │   ├── QuizQuestionWrapper.tsx
│   │   │   │   ├── QuoteCardWrapper.tsx
│   │   │   │   ├── ReactionBurstWrapper.tsx
│   │   │   │   ├── RoadmapLanesWrapper.tsx
│   │   │   │   ├── Scene3DWrapper.tsx
│   │   │   │   ├── ScrollingImagesWrapper.tsx
│   │   │   │   ├── SearchResultsPopulateWrapper.tsx
│   │   │   │   ├── SocialClipWrapper.tsx
│   │   │   │   ├── SportsScorebugWrapper.tsx
│   │   │   │   ├── StaggeredMotionWrapper.tsx
│   │   │   │   ├── StatCardWrapper.tsx
│   │   │   │   ├── TabSwitchPanelWrapper.tsx
│   │   │   │   ├── TerminalSimulatorWrapper.tsx
│   │   │   │   ├── THEMESWrapper.tsx
│   │   │   │   ├── TimelineStepsWrapper.tsx
│   │   │   │   ├── TitleCardWrapper.tsx
│   │   │   │   ├── TutorialClipWrapper.tsx
│   │   │   │   ├── TypeWriterWrapper.tsx
│   │   │   │   ├── WeatherCardWrapper.tsx
│   │   │   │   └── ZoomPanFrameWrapper.tsx
│   │   │   ├── scenes/
│   │   │   │   ├── AiComposerShowcaseWrapper.tsx
│   │   │   │   ├── AiGenerationCanvasWrapper.tsx
│   │   │   │   ├── AudiogramSceneWrapper.tsx
│   │   │   │   ├── BrowserFlowWrapper.tsx
│   │   │   │   ├── CaptionSceneWrapper.tsx
│   │   │   │   ├── CreatorReelWrapper.tsx
│   │   │   │   ├── DataFlowPipesWrapper.tsx
│   │   │   │   ├── DataStoryWrapper.tsx
│   │   │   │   ├── DragDropFlowWrapper.tsx
│   │   │   │   ├── EcosystemOrbitWrapper.tsx
│   │   │   │   ├── FormFillSequenceWrapper.tsx
│   │   │   │   ├── HeroDeviceAssembleWrapper.tsx
│   │   │   │   ├── HeroLoopWrapper.tsx
│   │   │   │   ├── IntroWrapper.tsx
│   │   │   │   ├── LandingCodeShowcaseWrapper.tsx
│   │   │   │   ├── LiveCodeSplitWrapper.tsx
│   │   │   │   ├── MediaSequenceWrapper.tsx
│   │   │   │   ├── ShowcaseWrapper.tsx
│   │   │   │   ├── SplitScreenWrapper.tsx
│   │   │   │   ├── TalkingHeadLayoutWrapper.tsx
│   │   │   │   ├── TeamGridWrapper.tsx
│   │   │   │   └── ToolMenuSlideWrapper.tsx
│   │   │   └── brand-resolver.ts
│   │   ├── types/
│   │   │   ├── ai_contracts.ts
│   │   │   ├── creative_contracts.ts
│   │   │   └── state.ts
│   │   ├── animations.ts
│   │   ├── BlueprintVideo.tsx
│   │   ├── BrandContext.tsx
│   │   ├── CanonicalVideo.tsx
│   │   ├── captionLayout.ts
│   │   ├── CursorInteractionContext.tsx
│   │   ├── fonts.ts
│   │   ├── index.ts
│   │   ├── loadProjectData.ts
│   │   ├── merge.ts
│   │   ├── Root.tsx
│   │   ├── rtl.css
│   │   ├── Showcase.tsx
│   │   └── TemplateGallery.tsx
│   ├── build_caption_props.py
│   ├── card_stack.json
│   ├── carousel.json
│   ├── components.json
│   ├── dependency_tree.json
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   ├── remotion-ui.json
│   ├── remotion.config.ts
│   ├── skills-lock.json
│   └── tsconfig.json
├── schemas/
│   ├── ai/
│   │   ├── ai_activity.schema.json
│   │   ├── ai_cache_entry.schema.json
│   │   ├── ai_contracts.schema.json
│   │   ├── ai_error.schema.json
│   │   ├── ai_request.schema.json
│   │   ├── ai_response.schema.json
│   │   ├── ai_run.schema.json
│   │   ├── ai_step.schema.json
│   │   ├── ai_trace.schema.json
│   │   ├── align_audio_metadata_input.schema.json
│   │   ├── align_audio_metadata_output.schema.json
│   │   ├── aligned_segment_item.schema.json
│   │   ├── aligned_word_item.schema.json
│   │   ├── analyze_loudness_input.schema.json
│   │   ├── analyze_loudness_output.schema.json
│   │   ├── audio_denoise_request.schema.json
│   │   ├── audio_denoise_result.schema.json
│   │   ├── audio_enhance_request.schema.json
│   │   ├── audio_enhance_result.schema.json
│   │   ├── audio_intelligence.schema.json
│   │   ├── audio_segment_item.schema.json
│   │   ├── auto_crop_image_request.schema.json
│   │   ├── auto_crop_image_result.schema.json
│   │   ├── auto_crop_input.schema.json
│   │   ├── auto_crop_output.schema.json
│   │   ├── background_removal_request.schema.json
│   │   ├── background_removal_result.schema.json
│   │   ├── benchmark_debt.schema.json
│   │   ├── cancel_job_input.schema.json
│   │   ├── cancel_job_output.schema.json
│   │   ├── capability_definition.schema.json
│   │   ├── capability_request.schema.json
│   │   ├── capability_result.schema.json
│   │   ├── change_video_speed_input.schema.json
│   │   ├── change_video_speed_output.schema.json
│   │   ├── check_cache_input.schema.json
│   │   ├── check_cache_output.schema.json
│   │   ├── concatenate_videos_input.schema.json
│   │   ├── concatenate_videos_output.schema.json
│   │   ├── convert_image_input.schema.json
│   │   ├── convert_image_output.schema.json
│   │   ├── convert_image_request.schema.json
│   │   ├── convert_image_result.schema.json
│   │   ├── cost_estimate.schema.json
│   │   ├── crop_image_ratio_request.schema.json
│   │   ├── crop_image_ratio_result.schema.json
│   │   ├── crop_ratio_input.schema.json
│   │   ├── crop_ratio_output.schema.json
│   │   ├── detect_black_frames_input.schema.json
│   │   ├── detect_black_frames_output.schema.json
│   │   ├── detect_silence_input.schema.json
│   │   ├── detect_silence_output.schema.json
│   │   ├── download_icon_input.schema.json
│   │   ├── download_icon_output.schema.json
│   │   ├── download_remote_media_input.schema.json
│   │   ├── download_remote_media_output.schema.json
│   │   ├── downloaded_asset_item.schema.json
│   │   ├── enforce_keyframes_input.schema.json
│   │   ├── enforce_keyframes_output.schema.json
│   │   ├── eval_dataset.schema.json
│   │   ├── eval_example.schema.json
│   │   ├── eval_result.schema.json
│   │   ├── extend_audio_input.schema.json
│   │   ├── extend_audio_output.schema.json
│   │   ├── extend_video_input.schema.json
│   │   ├── extend_video_output.schema.json
│   │   ├── extract_media_page_input.schema.json
│   │   ├── extract_media_page_output.schema.json
│   │   ├── get_job_status_input.schema.json
│   │   ├── get_job_status_output.schema.json
│   │   ├── icon_search_result_item.schema.json
│   │   ├── image_generation_request.schema.json
│   │   ├── image_generation_result.schema.json
│   │   ├── implementation_descriptor.schema.json
│   │   ├── inspect_media_input.schema.json
│   │   ├── inspect_media_output.schema.json
│   │   ├── lip_sync_request.schema.json
│   │   ├── lip_sync_result.schema.json
│   │   ├── media_intelligence.schema.json
│   │   ├── media_intelligence_ref.schema.json
│   │   ├── memory_query.schema.json
│   │   ├── memory_result.schema.json
│   │   ├── model_requirement.schema.json
│   │   ├── model_selection.schema.json
│   │   ├── mutate_asset_status_input.schema.json
│   │   ├── mutate_asset_status_output.schema.json
│   │   ├── normalize_audio_input.schema.json
│   │   ├── normalize_audio_output.schema.json
│   │   ├── normalize_loudness_input.schema.json
│   │   ├── normalize_loudness_output.schema.json
│   │   ├── optimize_image_input.schema.json
│   │   ├── optimize_image_output.schema.json
│   │   ├── optimize_image_request.schema.json
│   │   ├── optimize_image_result.schema.json
│   │   ├── person_segmentation_request.schema.json
│   │   ├── person_segmentation_result.schema.json
│   │   ├── prepare_image_asset_input.schema.json
│   │   ├── prepare_image_asset_output.schema.json
│   │   ├── prepare_image_asset_request.schema.json
│   │   ├── prepare_image_asset_result.schema.json
│   │   ├── prepare_vo_segments_input.schema.json
│   │   ├── prepare_vo_segments_output.schema.json
│   │   ├── prepared_vo_segment_item.schema.json
│   │   ├── probe_image_input.schema.json
│   │   ├── probe_image_output.schema.json
│   │   ├── probe_image_request.schema.json
│   │   ├── probe_image_result.schema.json
│   │   ├── prompt_contract.schema.json
│   │   ├── prompt_metadata.schema.json
│   │   ├── prompt_render_request.schema.json
│   │   ├── prompt_render_result.schema.json
│   │   ├── resize_image_request.schema.json
│   │   ├── resize_image_result.schema.json
│   │   ├── resize_video_input.schema.json
│   │   ├── resize_video_output.schema.json
│   │   ├── search_icons_input.schema.json
│   │   ├── search_icons_output.schema.json
│   │   ├── search_sound_effects_input.schema.json
│   │   ├── search_sound_effects_output.schema.json
│   │   ├── search_stock_audio_input.schema.json
│   │   ├── search_stock_audio_output.schema.json
│   │   ├── search_stock_images_input.schema.json
│   │   ├── search_stock_images_output.schema.json
│   │   ├── search_stock_videos_input.schema.json
│   │   ├── search_stock_videos_output.schema.json
│   │   ├── segment_speech_input.schema.json
│   │   ├── segment_speech_output.schema.json
│   │   ├── silence_interval_item.schema.json
│   │   ├── speech_intelligence.schema.json
│   │   ├── speech_manifest_input.schema.json
│   │   ├── speech_manifest_output.schema.json
│   │   ├── speech_text_segment_item.schema.json
│   │   ├── speech_timeline_input.schema.json
│   │   ├── speech_timeline_output.schema.json
│   │   ├── speech_to_text_input.schema.json
│   │   ├── split_speech_text_input.schema.json
│   │   ├── split_speech_text_output.schema.json
│   │   ├── stock_media_item.schema.json
│   │   ├── store_cache_input.schema.json
│   │   ├── store_cache_output.schema.json
│   │   ├── thumbnail_input.schema.json
│   │   ├── thumbnail_output.schema.json
│   │   ├── thumbnail_request.schema.json
│   │   ├── thumbnail_result.schema.json
│   │   ├── tool_call.schema.json
│   │   ├── tool_result.schema.json
│   │   ├── trace_span_record.schema.json
│   │   ├── trim_audio_input.schema.json
│   │   ├── trim_audio_output.schema.json
│   │   ├── trim_silence_input.schema.json
│   │   ├── trim_silence_output.schema.json
│   │   ├── trim_video_input.schema.json
│   │   ├── trim_video_output.schema.json
│   │   ├── tts_request.schema.json
│   │   ├── tts_result.schema.json
│   │   ├── upscale_image_input.schema.json
│   │   ├── upscale_image_output.schema.json
│   │   ├── upscale_request.schema.json
│   │   ├── upscale_result.schema.json
│   │   ├── usage_record.schema.json
│   │   ├── video_generation_request.schema.json
│   │   ├── video_generation_result.schema.json
│   │   ├── visual_intelligence.schema.json
│   │   ├── vocal_isolation_request.schema.json
│   │   └── vocal_isolation_result.schema.json
│   ├── creative/
│   │   ├── blueprint_compilation_result.schema.json
│   │   ├── candidate_gate_result.schema.json
│   │   ├── candidate_promotion_record.schema.json
│   │   ├── candidate_review_bundle.schema.json
│   │   ├── candidate_review_decision.schema.json
│   │   ├── candidate_validation_report.schema.json
│   │   ├── compose_component_ref.schema.json
│   │   ├── compose_evaluation_result.schema.json
│   │   ├── composition_layer.schema.json
│   │   ├── composition_plan.schema.json
│   │   ├── creative_brief.schema.json
│   │   ├── creative_case_grade.schema.json
│   │   ├── creative_conflict.schema.json
│   │   ├── creative_constraints.schema.json
│   │   ├── creative_contracts.schema.json
│   │   ├── creative_cost_audit_run.schema.json
│   │   ├── creative_eval_case.schema.json
│   │   ├── creative_eval_run.schema.json
│   │   ├── creative_feedback.schema.json
│   │   ├── creative_intent.schema.json
│   │   ├── creative_plan.schema.json
│   │   ├── creative_plan_validation_result.schema.json
│   │   ├── creative_project_cost_summary.schema.json
│   │   ├── creative_tier_decision.schema.json
│   │   ├── creative_usage_event.schema.json
│   │   ├── director_recommendation_bundle.schema.json
│   │   ├── effective_user_style.schema.json
│   │   ├── efficiency_finding.schema.json
│   │   ├── emotion_direction.schema.json
│   │   ├── feedback_classification.schema.json
│   │   ├── field_provenance.schema.json
│   │   ├── judge_calibration_record.schema.json
│   │   ├── knowledge_descriptor.schema.json
│   │   ├── motion_direction.schema.json
│   │   ├── narrative_beat.schema.json
│   │   ├── narrative_direction.schema.json
│   │   ├── narrative_plan.schema.json
│   │   ├── pairwise_grade_result.schema.json
│   │   ├── promotion_decision.schema.json
│   │   ├── promotion_manifest.schema.json
│   │   ├── recipe_definition.schema.json
│   │   ├── recipe_selection.schema.json
│   │   ├── recipe_stage.schema.json
│   │   ├── resolved_creative_guidance.schema.json
│   │   ├── resolved_template_decision.schema.json
│   │   ├── reuse_candidate_score.schema.json
│   │   ├── reuse_evaluation_result.schema.json
│   │   ├── scene_intent.schema.json
│   │   ├── sfx_direction.schema.json
│   │   ├── skill_definition.schema.json
│   │   ├── style_decision_trace.schema.json
│   │   ├── style_preference_provenance.schema.json
│   │   ├── taste_context.schema.json
│   │   ├── taste_decision.schema.json
│   │   ├── taste_rule.schema.json
│   │   ├── template_candidate.schema.json
│   │   ├── trace_assertion.schema.json
│   │   ├── trace_assertion_result.schema.json
│   │   ├── user_style_profile.schema.json
│   │   └── validation_snapshot.schema.json
│   ├── examples/
│   │   └── prj_demo/
│   │       ├── blueprint.json
│   │       ├── brand.json
│   │       ├── manifest.json
│   │       ├── overrides.json
│   │       ├── project.json
│   │       └── state.json
│   ├── blueprint.schema.json
│   ├── brand.schema.json
│   ├── manifest.schema.json
│   ├── manifest.v2.schema.json
│   ├── overrides.schema.json
│   ├── project.schema.json
│   ├── state.schema.json
│   └── template_proposal_schema.json
├── scripts/
│   ├── archive/
│   │   ├── phase13/
│   │   │   ├── baseline.ts
│   │   │   ├── coverage.ts
│   │   │   └── prioritize.ts
│   │   ├── phase14/
│   │   │   ├── baseline.ts
│   │   │   ├── execution_bridge_audit.ts
│   │   │   ├── patch_candidates.ts
│   │   │   └── prioritize.ts
│   │   ├── phase15/
│   │   │   ├── build_execution_cohorts.ts
│   │   │   ├── generate_sample_batch.ts
│   │   │   ├── validate_execution_contracts.ts
│   │   │   └── validate_verification_integrity.ts
│   │   ├── phase16/
│   │   │   ├── build_16_3_coverage_report.ts
│   │   │   ├── build_blocked_inventory.ts
│   │   │   ├── build_phase_16_3_inventory.ts
│   │   │   ├── build_phase_16_4_analysis.ts
│   │   │   ├── build_phase_16_4_inventory.ts
│   │   │   ├── extract_proven_defaults.ts
│   │   │   ├── generate_16_3_runtime_batch.ts
│   │   │   ├── mine_adapter_families.ts
│   │   │   ├── rank_adapter_families.ts
│   │   │   ├── test_social_captions_adapter.ts
│   │   │   ├── validate_phase_16_2.ts
│   │   │   └── validate_phase_16_3.ts
│   │   ├── __init__.py
│   │   ├── classify_templates.py
│   │   ├── migrate_assets.py
│   │   ├── migrate_legacy_projects.py
│   │   ├── migrate_state.py
│   │   ├── smoke_crd019_templates.py
│   │   ├── smoke_crd020_temporal.py
│   │   └── stitch_skill.py
│   ├── ci/
│   │   └── run_required_checks.sh
│   ├── core/
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   └── postgres_memory_repository.py
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── command_policy.py
│   │   │   ├── env_policy.py
│   │   │   ├── path_policy.py
│   │   │   ├── permissions.py
│   │   │   ├── principal.py
│   │   │   └── settings.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   └── storage_service.py
│   │   ├── __init__.py
│   │   ├── ai_cache_repository.py
│   │   ├── ai_prompt_repository.py
│   │   ├── ai_run_repository.py
│   │   ├── ai_trace_repository.py
│   │   ├── artifact_service.py
│   │   ├── asset_cache.py
│   │   ├── asset_lifecycle.py
│   │   ├── asset_resolution.py
│   │   ├── authoring_idempotency_repository.py
│   │   ├── authority_matrix.py
│   │   ├── blueprint_compiler.py
│   │   ├── blueprint_errors.py
│   │   ├── blueprint_loader.py
│   │   ├── blueprint_migration.py
│   │   ├── blueprint_model.py
│   │   ├── blueprint_validator.py
│   │   ├── budget_service.py
│   │   ├── canonical_asset_repository.py
│   │   ├── canonical_document_repository.py
│   │   ├── database.py
│   │   ├── dependency_graph.py
│   │   ├── e2e_data_render.py
│   │   ├── evidence_matrix.py
│   │   ├── failure_injection.py
│   │   ├── failure_model.py
│   │   ├── idempotency_repository.py
│   │   ├── idempotency_store.py
│   │   ├── lifecycle_service.py
│   │   ├── manifest_errors.py
│   │   ├── manifest_loader.py
│   │   ├── manifest_migration.py
│   │   ├── manifest_model.py
│   │   ├── manifest_validator.py
│   │   ├── materializer.py
│   │   ├── media_intelligence_repository.py
│   │   ├── probe_planner.py
│   │   ├── project_identity.py
│   │   ├── project_lock.py
│   │   ├── recovery_engine.py
│   │   ├── render_input.py
│   │   ├── retry_policy.py
│   │   ├── review_service.py
│   │   ├── run_model.py
│   │   ├── run_repository.py
│   │   ├── runtime_logger.py
│   │   ├── session_manager.py
│   │   ├── state_lock.py
│   │   ├── state_model.py
│   │   ├── state_store.py
│   │   ├── template_candidate_repository.py
│   │   ├── template_contract.py
│   │   ├── template_registry_publisher.py
│   │   ├── tenant_model.py
│   │   └── worker.py
│   ├── gates/
│   │   ├── __init__.py
│   │   ├── asset_gate.py
│   │   ├── code_template_gate.py
│   │   ├── final_qc.py
│   │   ├── motion_validator.py
│   │   ├── plan_gate.py
│   │   ├── probe_qc.py
│   │   ├── smart_qc.py
│   │   ├── taste_gate.py
│   │   ├── validate_blueprint.py
│   │   └── vo_quality_check.py
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── build_asset_index.py
│   │   ├── build_catalog.py
│   │   ├── build_ground_truth.py
│   │   ├── generate_drift_matrix.py
│   │   ├── generate_matrix.ts
│   │   ├── generate_plan.py
│   │   ├── generate_registry.ts
│   │   ├── generate_s28_legacy_inventory.py
│   │   ├── generate_schema.ts
│   │   ├── generate_template_aliases.py
│   │   ├── generate_template_contract.py
│   │   └── materialize_project.py
│   ├── governance/
│   │   ├── governance_audit.py
│   │   └── simulate_ci_gate.ps1
│   ├── maintenance/
│   │   ├── __init__.py
│   │   ├── auto_backup.py
│   │   ├── batch_builder.py
│   │   ├── check_orphans.py
│   │   ├── cleanup_assets.py
│   │   ├── generate_file_tree.py
│   │   ├── promote_template.py
│   │   ├── retier_docs.py
│   │   ├── scene_compiler.py
│   │   ├── setup_docker.py
│   │   ├── sync_templates.py
│   │   ├── template_router.py
│   │   ├── transcript_cleaner.py
│   │   └── update_schema.py
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── benchmark_guards.py
│   │   ├── health.py
│   │   ├── metrics_collector.py
│   │   └── metrics_model.py
│   ├── remotion-app/
│   │   └── src/
│   │       └── templates/  [مجلد وسائط مستثناة أو فارغ]
│   ├── remotion_interop/
│   │   ├── __init__.py
│   │   ├── analyze_adapter_families.ts
│   │   ├── build_video.ts
│   │   ├── certify_templates.ts
│   │   ├── enforce_contracts.ts
│   │   ├── infer_schemas_ast.ts
│   │   └── tsconfig.json
│   ├── security/
│   │   ├── __init__.py
│   │   ├── path_security.py
│   │   └── security.py
│   ├── testing/
│   │   └── s28_r15_soak_and_load_runner.py
│   ├── tests/
│   │   ├── compiler.test.ts
│   │   ├── orchestration.test.ts
│   │   ├── phase11.test.ts
│   │   ├── phase12.test.ts
│   │   └── registry.test.ts
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── audit_imports.py
│   │   ├── audit_skill.py
│   │   ├── candidate_ast_worker.cjs
│   │   ├── candidate_runtime_runner.py
│   │   ├── check_dependencies_lock.py
│   │   ├── check_ground_truth_sync.py
│   │   ├── check_secrets.py
│   │   ├── custom_code_validator.py
│   │   ├── inspect_template.py
│   │   ├── spec_validator.py
│   │   ├── template_lint.py
│   │   ├── template_proposal_validator.py
│   │   ├── validate_schemas.py
│   │   ├── validate_template.py
│   │   ├── verify_links.py
│   │   └── verify_media_layer.py
│   ├── verify/
│   │   ├── contact-sheet.sh
│   │   ├── probe-mp4.sh
│   │   ├── README.md
│   │   ├── seek-shot.sh
│   │   └── verify_preview.py
│   ├── assemble_m02_master_report.py
│   ├── ci_run_all.py
│   ├── execute_authoring_mutation.ts
│   ├── generate_ai_contracts.py
│   ├── generate_creative_contracts.py
│   ├── open_studio.py
│   ├── pipeline.py
│   ├── render_project.py
│   ├── render_via_adapter.ts
│   ├── render_via_planner.ts
│   ├── run_creative_cost_audit.py
│   ├── run_creative_e2e.py
│   ├── run_creative_regression.py
│   ├── run_real_cost_performance_benchmark.py
│   ├── scaffold_project.py
│   ├── smoke_openrouter.py
│   └── worker.py
├── templates/
│   ├── custom/
│   │   ├── LevelOneScene.tsx
│   │   └── LevelZeroBox.tsx
│   ├── effects/
│   │   ├── BookFlipTransition.tsx
│   │   ├── ClockWipeTransition.tsx
│   │   ├── CrosswarpTransition.tsx
│   │   ├── CrossZoomTransition.tsx
│   │   ├── DissolveTransition.tsx
│   │   ├── DreamyZoomTransition.tsx
│   │   ├── engine-bridge.tsx
│   │   ├── FadeTransition.tsx
│   │   ├── FilmBurnTransition.tsx
│   │   ├── FlipTransition.tsx
│   │   ├── IrisTransition.tsx
│   │   ├── LinearBlurTransition.tsx
│   │   ├── PushCutTransition.tsx
│   │   ├── RippleTransition.tsx
│   │   ├── SlideTransition.tsx
│   │   ├── SwapTransition.tsx
│   │   ├── WipeTransition.tsx
│   │   ├── ZoomBlurTransition.tsx
│   │   └── ZoomInOutTransition.tsx
│   ├── elements/
│   │   ├── AnimatedBarChartWrapper.tsx
│   │   ├── AnimatedCounterWrapper.tsx
│   │   ├── AnimatedTextWrapper.tsx
│   │   ├── AutoFitTitleWrapper.tsx
│   │   ├── BentoPanWrapper.tsx
│   │   ├── BRollStackWrapper.tsx
│   │   ├── CalendarMonthFillWrapper.tsx
│   │   ├── CalloutSpotlightWrapper.tsx
│   │   ├── CaptionBumperWrapper.tsx
│   │   ├── ChangelogEntryWrapper.tsx
│   │   ├── ChatToPreviewWrapper.tsx
│   │   ├── CodeAccordionWrapper.tsx
│   │   ├── CodeBlockWrapper.tsx
│   │   ├── CodeDiffWipeWrapper.tsx
│   │   ├── CodeRevealWrapper.tsx
│   │   ├── CommentCalloutWrapper.tsx
│   │   ├── CommitGraphWrapper.tsx
│   │   ├── ComparisonTableWrapper.tsx
│   │   ├── CountdownTimerWrapper.tsx
│   │   ├── DashboardPopulateWrapper.tsx
│   │   ├── DeployRevealWrapper.tsx
│   │   ├── DeviceMockupZoomWrapper.tsx
│   │   ├── EndCardWrapper.tsx
│   │   ├── FaqAccordionWrapper.tsx
│   │   ├── FeatureListWrapper.tsx
│   │   ├── FileTreeRevealWrapper.tsx
│   │   ├── GradientWrapper.tsx
│   │   ├── HookCardWrapper.tsx
│   │   ├── ImageExpandWrapper.tsx
│   │   ├── KanbanMoveWrapper.tsx
│   │   ├── LogoRevealWrapper.tsx
│   │   ├── LogoWallWrapper.tsx
│   │   ├── LowerThirdWrapper.tsx
│   │   ├── MapFlightWrapper.tsx
│   │   ├── MatrixRainWrapper.tsx
│   │   ├── MediaFrameWrapper.tsx
│   │   ├── MetricTickerWrapper.tsx
│   │   ├── NewsTickerBarWrapper.tsx
│   │   ├── NotificationStackWrapper.tsx
│   │   ├── OrgChartBuildWrapper.tsx
│   │   ├── ParticleSystemWrapper.tsx
│   │   ├── PodcastClipWrapper.tsx
│   │   ├── PollOverlayWrapper.tsx
│   │   ├── PricingCardWrapper.tsx
│   │   ├── PricingFocusWrapper.tsx
│   │   ├── QuizQuestionWrapper.tsx
│   │   ├── QuoteCardWrapper.tsx
│   │   ├── ReactionBurstWrapper.tsx
│   │   ├── RoadmapLanesWrapper.tsx
│   │   ├── Scene3DWrapper.tsx
│   │   ├── ScrollingImagesWrapper.tsx
│   │   ├── SearchResultsPopulateWrapper.tsx
│   │   ├── SocialClipWrapper.tsx
│   │   ├── SportsScorebugWrapper.tsx
│   │   ├── StaggeredMotionWrapper.tsx
│   │   ├── StatCardWrapper.tsx
│   │   ├── TabSwitchPanelWrapper.tsx
│   │   ├── TerminalSimulatorWrapper.tsx
│   │   ├── THEMESWrapper.tsx
│   │   ├── TimelineStepsWrapper.tsx
│   │   ├── TitleCardWrapper.tsx
│   │   ├── TutorialClipWrapper.tsx
│   │   ├── TypeWriterWrapper.tsx
│   │   ├── WeatherCardWrapper.tsx
│   │   └── ZoomPanFrameWrapper.tsx
│   ├── scenes/
│   │   ├── AiComposerShowcaseWrapper.tsx
│   │   ├── AiGenerationCanvasWrapper.tsx
│   │   ├── AudiogramSceneWrapper.tsx
│   │   ├── BrowserFlowWrapper.tsx
│   │   ├── CaptionSceneWrapper.tsx
│   │   ├── CreatorReelWrapper.tsx
│   │   ├── DataFlowPipesWrapper.tsx
│   │   ├── DataStoryWrapper.tsx
│   │   ├── DragDropFlowWrapper.tsx
│   │   ├── EcosystemOrbitWrapper.tsx
│   │   ├── FormFillSequenceWrapper.tsx
│   │   ├── HeroDeviceAssembleWrapper.tsx
│   │   ├── HeroLoopWrapper.tsx
│   │   ├── IntroWrapper.tsx
│   │   ├── LandingCodeShowcaseWrapper.tsx
│   │   ├── LiveCodeSplitWrapper.tsx
│   │   ├── MediaSequenceWrapper.tsx
│   │   ├── ShowcaseWrapper.tsx
│   │   ├── SplitScreenWrapper.tsx
│   │   ├── TalkingHeadLayoutWrapper.tsx
│   │   ├── TeamGridWrapper.tsx
│   │   └── ToolMenuSlideWrapper.tsx
│   └── brand-resolver.ts
├── tests/
│   ├── ai/
│   │   ├── acquisition/
│   │   │   ├── __init__.py
│   │   │   ├── test_contracts_and_normalization.py
│   │   │   ├── test_dedupe_and_cache.py
│   │   │   ├── test_e2e_acquisition_pipeline.py
│   │   │   ├── test_filtering_and_ranking.py
│   │   │   ├── test_legacy_parity.py
│   │   │   ├── test_live_smoke.py
│   │   │   ├── test_provider_fault_tolerance.py
│   │   │   ├── test_safe_downloader_and_security.py
│   │   │   └── test_tool_gateway_acquisition.py
│   │   ├── audio/
│   │   │   ├── test_audio_benchmark.py
│   │   │   ├── test_audio_mode_engine.py
│   │   │   ├── test_audio_pipeline.py
│   │   │   └── test_dsp_analysis.py
│   │   ├── audio_modernization/
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_audio_analysis.py
│   │   │   ├── test_audio_contracts.py
│   │   │   ├── test_fault_injection.py
│   │   │   ├── test_parity_matrix.py
│   │   │   ├── test_security.py
│   │   │   ├── test_speech_preparation.py
│   │   │   ├── test_tenant_isolation.py
│   │   │   └── test_voiceover_manifest_and_timeline.py
│   │   ├── audit/
│   │   │   ├── test_s27_final_architecture_audit.py
│   │   │   ├── test_s28_inventory.py
│   │   │   └── test_s28_m11_final_architecture_audit.py
│   │   ├── batch/
│   │   │   └── test_batch_execution.py
│   │   ├── benchmark/
│   │   │   └── test_cost_and_performance_benchmark.py
│   │   ├── budget/
│   │   │   ├── test_accounting.py
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_concurrency.py
│   │   │   ├── test_estimator.py
│   │   │   ├── test_idempotency.py
│   │   │   ├── test_invariants.py
│   │   │   ├── test_release.py
│   │   │   ├── test_reservation.py
│   │   │   ├── test_scopes.py
│   │   │   └── test_settlement.py
│   │   ├── cache/
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_cache_architecture_and_boundaries.py
│   │   │   ├── test_cache_key.py
│   │   │   ├── test_cache_policy.py
│   │   │   ├── test_cache_repository.py
│   │   │   ├── test_cache_service.py
│   │   │   ├── test_concurrency_coalescing.py
│   │   │   ├── test_crash_recovery.py
│   │   │   ├── test_crash_recovery_coalesced.py
│   │   │   ├── test_durable_activity_integration.py
│   │   │   ├── test_poisoning_and_invalidation.py
│   │   │   └── test_tenant_isolation.py
│   │   ├── candidates/
│   │   │   ├── conftest.py
│   │   │   ├── test_candidate_adversarial_closure.py
│   │   │   ├── test_candidate_architecture_guards.py
│   │   │   ├── test_candidate_concurrency.py
│   │   │   ├── test_candidate_contracts.py
│   │   │   ├── test_candidate_hashing.py
│   │   │   ├── test_candidate_lifecycle_e2e.py
│   │   │   ├── test_candidate_promotion_service.py
│   │   │   ├── test_candidate_registry_isolation.py
│   │   │   ├── test_candidate_review_workflow.py
│   │   │   ├── test_candidate_runtime_validation.py
│   │   │   ├── test_candidate_service.py
│   │   │   ├── test_candidate_static_validation.py
│   │   │   ├── test_candidate_storage.py
│   │   │   ├── test_candidate_tenant_isolation.py
│   │   │   └── test_candidate_validation_tenant_isolation.py
│   │   ├── capabilities/
│   │   │   └── test_capability_registry.py
│   │   ├── conflict/
│   │   │   └── test_conflict_resolver.py
│   │   ├── context/
│   │   │   ├── conftest.py
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_budgeting.py
│   │   │   ├── test_builder.py
│   │   │   ├── test_compression.py
│   │   │   ├── test_conflicts.py
│   │   │   ├── test_deduplication.py
│   │   │   ├── test_determinism.py
│   │   │   ├── test_irrelevant_memory.py
│   │   │   ├── test_needs.py
│   │   │   ├── test_ranking.py
│   │   │   ├── test_retrieval.py
│   │   │   ├── test_tenant_isolation.py
│   │   │   └── test_token_safety.py
│   │   ├── contracts/
│   │   │   ├── fixtures/
│   │   │   │   └── creative_contract_fixtures.json
│   │   │   ├── fixtures.py
│   │   │   ├── test_capability_taxonomy_and_contracts.py
│   │   │   ├── test_contracts_invalid.py
│   │   │   ├── test_contracts_valid.py
│   │   │   ├── test_creative_contracts.py
│   │   │   ├── test_generator_sync.py
│   │   │   ├── test_no_dict_any.py
│   │   │   ├── test_provider_bypass_guards.py
│   │   │   ├── test_provider_neutrality.py
│   │   │   ├── test_schema_parity.py
│   │   │   └── test_semantic_invariants.py
│   │   ├── cost/
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_cost_attribution_and_summary.py
│   │   │   ├── test_cost_semantics_closeout.py
│   │   │   ├── test_efficiency_analyzer.py
│   │   │   ├── test_regression_integration.py
│   │   │   ├── test_tenant_isolation.py
│   │   │   ├── test_token_accounting.py
│   │   │   └── test_usage_event_contracts.py
│   │   ├── directors/
│   │   │   └── test_creative_directors.py
│   │   ├── e2e/
│   │   │   ├── test_full_creative_e2e_matrix.py
│   │   │   ├── test_multi_tenant_production_e2e.py
│   │   │   ├── test_real_service_e2e_closeout.py
│   │   │   ├── test_s28_m11_product_e2e_matrix.py
│   │   │   └── test_s28_m_automatic_stock_preparation.py
│   │   ├── evals/
│   │   │   ├── datasets/
│   │   │   │   ├── intent_dataset.json
│   │   │   │   └── recipe_selection_matrix.json
│   │   │   ├── test_creative_evals.py
│   │   │   ├── test_creative_evals_s28_04.py
│   │   │   ├── test_eval_platform.py
│   │   │   └── test_knowledge_and_skill_evals.py
│   │   ├── fault_injection/
│   │   │   ├── __init__.py
│   │   │   ├── contracts.py
│   │   │   ├── harness.py
│   │   │   ├── test_cascades_and_recovery.py
│   │   │   ├── test_full_fault_injection.py
│   │   │   ├── test_s28_m10_fault_injection.py
│   │   │   └── test_system_fault_injection.py
│   │   ├── feedback/
│   │   │   ├── test_feedback_classification.py
│   │   │   ├── test_feedback_learning_service.py
│   │   │   └── test_feedback_tenant_isolation.py
│   │   ├── image_modernization/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py
│   │   │   ├── test_adapter_and_gateway.py
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_fault_injection.py
│   │   │   ├── test_image_cache.py
│   │   │   ├── test_image_contracts.py
│   │   │   ├── test_image_security.py
│   │   │   ├── test_image_service.py
│   │   │   └── test_parity_matrix.py
│   │   ├── integration/
│   │   │   ├── test_knowledge_skill_integration.py
│   │   │   ├── test_s28_03_e2e_pipeline.py
│   │   │   └── test_s28_04_integration.py
│   │   ├── intent/
│   │   │   └── test_intent_parser.py
│   │   ├── knowledge/
│   │   │   └── test_knowledge_platform.py
│   │   ├── mcp/
│   │   │   ├── __init__.py
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_behavior_parity.py
│   │   │   ├── test_development_agent_preservation.py
│   │   │   ├── test_mcp_catalog.py
│   │   │   ├── test_mcp_compatibility_facade.py
│   │   │   ├── test_mcp_contracts.py
│   │   │   └── test_mcp_security_adversarial.py
│   │   ├── media_intelligence/
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_media_contracts.py
│   │   │   ├── test_media_service.py
│   │   │   └── test_technical_probe.py
│   │   ├── media_processing/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py
│   │   │   ├── test_adapter.py
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_contracts.py
│   │   │   ├── test_fault_injection.py
│   │   │   ├── test_parity_matrix.py
│   │   │   ├── test_security.py
│   │   │   ├── test_service.py
│   │   │   └── test_validator.py
│   │   ├── memory/
│   │   │   ├── test_100_messages.py
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_embeddings.py
│   │   │   ├── test_in_memory_repository.py
│   │   │   ├── test_large_artifacts.py
│   │   │   ├── test_models.py
│   │   │   ├── test_normalization.py
│   │   │   ├── test_postgres_memory_repository.py
│   │   │   ├── test_project_memory_boundary.py
│   │   │   ├── test_serialization.py
│   │   │   ├── test_tenant_isolation.py
│   │   │   └── test_write_policy.py
│   │   ├── migration/
│   │   │   └── test_legacy_migration.py
│   │   ├── models/
│   │   │   └── test_models.py
│   │   ├── narrative/
│   │   │   ├── test_narrative_metrics.py
│   │   │   └── test_narrative_planner.py
│   │   ├── observability/
│   │   │   ├── test_metrics.py
│   │   │   ├── test_redaction.py
│   │   │   └── test_tracer.py
│   │   ├── orchestration/
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_cancellation.py
│   │   │   ├── test_crash_recovery.py
│   │   │   ├── test_dag.py
│   │   │   ├── test_dag_execution_and_dependencies.py
│   │   │   ├── test_failure_propagation_and_retries.py
│   │   │   ├── test_repository_persistence.py
│   │   │   ├── test_restart_foundation_proof.py
│   │   │   ├── test_state_machines.py
│   │   │   ├── test_tenant_isolation.py
│   │   │   └── test_worker_claims_and_leases.py
│   │   ├── parity/
│   │   │   ├── test_full_capability_parity.py
│   │   │   └── test_m09_residual_disposition.py
│   │   ├── performance/
│   │   │   └── test_s28_m10_performance_baseline.py
│   │   ├── planning/
│   │   │   ├── conftest.py
│   │   │   ├── test_blueprint_compiler.py
│   │   │   ├── test_compiler_negative.py
│   │   │   ├── test_compose_engine.py
│   │   │   ├── test_creative_plan_validator.py
│   │   │   ├── test_creative_planner.py
│   │   │   ├── test_planner_personalization.py
│   │   │   ├── test_planning_architecture_guards.py
│   │   │   ├── test_reuse_engine.py
│   │   │   ├── test_s28_05_e2e_integration.py
│   │   │   ├── test_s28_06_integration.py
│   │   │   └── test_tier_policy.py
│   │   ├── prompts/
│   │   │   ├── test_prompt_cache.py
│   │   │   └── test_prompt_registry.py
│   │   ├── providers/
│   │   │   ├── test_openrouter.py
│   │   │   └── test_providers.py
│   │   ├── recipes/
│   │   │   ├── test_hard_eligibility_gate_proof.py
│   │   │   ├── test_recipe_compliance_audit.py
│   │   │   ├── test_recipe_registry.py
│   │   │   └── test_recipe_selector.py
│   │   ├── regression/
│   │   │   ├── test_all_eval_categories.py
│   │   │   ├── test_deliberately_bad_detection.py
│   │   │   ├── test_personalization_regression.py
│   │   │   ├── test_regression_contracts.py
│   │   │   ├── test_regression_runner.py
│   │   │   ├── test_retrieval_metrics.py
│   │   │   ├── test_rubric_and_calibration.py
│   │   │   ├── test_s28_08b_architecture_guards.py
│   │   │   └── test_trace_grader.py
│   │   ├── routing/
│   │   │   ├── test_capability_router.py
│   │   │   ├── test_constraints.py
│   │   │   ├── test_determinism.py
│   │   │   ├── test_escalation.py
│   │   │   ├── test_fallback.py
│   │   │   ├── test_provider_neutrality.py
│   │   │   ├── test_router.py
│   │   │   ├── test_scoring.py
│   │   │   └── test_simulation.py
│   │   ├── security/
│   │   │   ├── test_ai_security.py
│   │   │   ├── test_knowledge_skill_security.py
│   │   │   ├── test_s28_03_architecture_guards.py
│   │   │   └── test_s28_m10_security_campaign.py
│   │   ├── skills/
│   │   │   └── test_skill_platform.py
│   │   ├── specialized/
│   │   │   ├── test_durability_and_cache.py
│   │   │   ├── test_failure_handling.py
│   │   │   ├── test_provider_swap.py
│   │   │   ├── test_routing_and_budget.py
│   │   │   ├── test_specialized_contracts.py
│   │   │   └── test_tenant_isolation.py
│   │   ├── speech/
│   │   │   ├── test_benchmark_harness.py
│   │   │   ├── test_benchmark_metrics.py
│   │   │   ├── test_language_and_code_switching.py
│   │   │   ├── test_provider_swap.py
│   │   │   ├── test_real_human_speech_validation.py
│   │   │   ├── test_reconciliation.py
│   │   │   ├── test_semantic_validators.py
│   │   │   ├── test_speech_canonicalization.py
│   │   │   ├── test_stt_cache_and_artifacts.py
│   │   │   ├── test_stt_canonical_integration.py
│   │   │   ├── test_stt_parity_matrix.py
│   │   │   ├── test_stt_provider_interface.py
│   │   │   └── test_stt_tenant_and_security.py
│   │   ├── style/
│   │   │   ├── test_current_request_wins.py
│   │   │   ├── test_style_resolver_precedence.py
│   │   │   └── test_user_style_profile.py
│   │   ├── taste/
│   │   │   ├── test_taste_engine.py
│   │   │   └── test_taste_registry.py
│   │   ├── tools/
│   │   │   ├── test_architecture_guards.py
│   │   │   ├── test_authorization.py
│   │   │   ├── test_context_builder_integration.py
│   │   │   ├── test_contracts.py
│   │   │   ├── test_dispatcher.py
│   │   │   ├── test_domain_adapters.py
│   │   │   ├── test_e2e_tool_integration.py
│   │   │   ├── test_registry.py
│   │   │   ├── test_security_adversarial.py
│   │   │   └── test_tool_gateway.py
│   │   ├── vision/
│   │   │   ├── test_adaptive_resolution.py
│   │   │   ├── test_keyframe_selection.py
│   │   │   ├── test_object_person.py
│   │   │   ├── test_ocr.py
│   │   │   ├── test_shot_detection.py
│   │   │   ├── test_vision_benchmark.py
│   │   │   └── test_vision_pipeline.py
│   │   ├── test_ai14_cross_cutting.py
│   │   ├── test_ai14_final_integration_proof.py
│   │   ├── test_ai_architecture_guards.py
│   │   ├── test_creative_architecture_guards.py
│   │   ├── test_provider_neutrality_architecture.py
│   │   ├── test_s28_08a_architecture_guards.py
│   │   ├── test_s28_h02_remediation.py
│   │   └── test_s28_h03_remediation.py
│   ├── api/
│   │   ├── test_candidate_promotions_router.py
│   │   ├── test_candidate_reviews_router.py
│   │   ├── test_client_without_filesystem.py
│   │   ├── test_gates.py
│   │   ├── test_health_readiness.py
│   │   ├── test_lifecycle_bypass_prevention.py
│   │   ├── test_pipeline_service.py
│   │   ├── test_project_creation.py
│   │   ├── test_projects.py
│   │   ├── test_render.py
│   │   └── test_tenant_endpoints.py
│   ├── architecture/
│   │   ├── test_adapter_layer_rules.py
│   │   ├── test_architecture_guards.py
│   │   ├── test_contract_authority_matrix.py
│   │   ├── test_gate_facade_guard.py
│   │   ├── test_import_restrictions.py
│   │   ├── test_lifecycle_authority_guard.py
│   │   ├── test_no_parallel_pipeline.py
│   │   ├── test_plugin_architecture_boundary.py
│   │   ├── test_quarantine_isolation.py
│   │   ├── test_review_authority_guard.py
│   │   ├── test_s14_architecture_guard.py
│   │   ├── test_s15_architecture_guard.py
│   │   ├── test_s17_architecture_guard.py
│   │   ├── test_s18_architecture_guard.py
│   │   ├── test_s19_architecture_guard.py
│   │   ├── test_s20_architecture_guard.py
│   │   ├── test_s21_architecture_guards.py
│   │   ├── test_s22_architecture_guards.py
│   │   ├── test_s23_architecture_guards.py
│   │   ├── test_s24_5_architecture_guards.py
│   │   ├── test_s24_architecture_guards.py
│   │   ├── test_s28_r02_architecture_guards.py
│   │   ├── test_s28_r02_architecture_guards.test.ts
│   │   ├── test_s28_r03_architecture_guards.test.ts
│   │   ├── test_s28_r04_architecture_guards.test.ts
│   │   ├── test_s28_r05_architecture_guards.test.ts
│   │   ├── test_s28_r06_architecture_guards.test.ts
│   │   ├── test_s28_r07_architecture_guards.test.ts
│   │   ├── test_s28_r07b_architecture_guards.test.ts
│   │   ├── test_s28_r08_architecture_guards.py
│   │   ├── test_s28_r08_architecture_guards.test.ts
│   │   ├── test_s28_r09_architecture_guards.py
│   │   ├── test_s28_r09_architecture_guards.test.ts
│   │   ├── test_s28_r10_architecture_guards.py
│   │   ├── test_s28_r10_architecture_guards.test.ts
│   │   ├── test_s28_r11_architecture_guards.py
│   │   ├── test_s28_r11_architecture_guards.test.ts
│   │   ├── test_s28_r12_architecture_guards.py
│   │   ├── test_s28_r12_architecture_guards.test.ts
│   │   ├── test_s28_r13_architecture_guards.py
│   │   ├── test_s28_r13_architecture_guards.test.ts
│   │   ├── test_s28_r14_architecture_guards.py
│   │   ├── test_s28_r14_architecture_guards.test.ts
│   │   ├── test_s28_r15_architecture_guards.py
│   │   ├── test_s28_r15_architecture_guards.test.ts
│   │   ├── test_state_file_integrity.py
│   │   └── test_state_transaction_guard.py
│   ├── archive/
│   │   └── test_migrate_legacy.py
│   ├── contracts/
│   │   ├── test_pipeline_service_contract.py
│   │   └── test_state_schema.py
│   ├── core/
│   │   ├── test_asset_resolution.py
│   │   ├── test_cross_tenant_asset_resolution.py
│   │   ├── test_evidence_matrix.py
│   │   ├── test_failure_classification.py
│   │   ├── test_lifecycle_service.py
│   │   ├── test_project_identity_matrix.py
│   │   ├── test_recovery_rollback.py
│   │   ├── test_runtime_logger.py
│   │   ├── test_s07_5_hardening.py
│   │   ├── test_s08_failure_retry.py
│   │   ├── test_s09_review_service.py
│   │   ├── test_s10_dependency_graph.py
│   │   ├── test_s11_manifest_v2_acceptance.py
│   │   ├── test_s12_blueprint_canonical_acceptance.py
│   │   ├── test_s12_cross_language_parity.py
│   │   ├── test_s13_transactional_materializer.py
│   │   ├── test_s17_render_input.py
│   │   ├── test_s18_probe_qc.py
│   │   ├── test_s28_r14_production_integration.py
│   │   ├── test_s28_r15_destruction_and_fault.py
│   │   ├── test_s28_r15_postgres_and_s3_closure.py
│   │   ├── test_safe_retry.py
│   │   ├── test_security_scaffolding.py
│   │   ├── test_state_store_cas.py
│   │   ├── test_state_store_tenant_cas.py
│   │   ├── test_storage_service.py
│   │   ├── test_template_candidate_repository.py
│   │   ├── test_template_contract.py
│   │   ├── test_tenant_database.py
│   │   ├── test_trace_identity.py
│   │   ├── test_version_compatibility_matrix.py
│   │   └── test_worker_ephemeral_workspace.py
│   ├── documentation/
│   │   ├── test_agents_md_accuracy.py
│   │   ├── test_architecture_truth.py
│   │   └── test_references_validity.py
│   ├── e2e/
│   │   ├── test_pipeline_integration.py
│   │   ├── test_saas_multi_tenant_e2e.py
│   │   ├── test_unified_pipeline.py
│   │   └── true_e2e_suite.py
│   ├── factories/
│   │   └── canonical_factory.py
│   ├── fault_injection/
│   │   ├── __init__.py
│   │   ├── test_fi_01_db_outage_transition.py
│   │   ├── test_fi_02_lease_fencing.py
│   │   ├── test_fi_03_worker_hard_death.py
│   │   ├── test_fi_04_api_hard_death.py
│   │   ├── test_fi_05_storage_outage.py
│   │   ├── test_fi_06_partial_upload.py
│   │   ├── test_fi_07_db_storage_disagreement.py
│   │   ├── test_fi_08_multiprocess_cas.py
│   │   ├── test_fi_09_idempotency.py
│   │   ├── test_fi_10_cross_tenant_access.py
│   │   ├── test_fi_11_cross_tenant_indirect_ref.py
│   │   ├── test_fi_12_rbac_matrix.py
│   │   ├── test_fi_13_tenant_spoofing.py
│   │   ├── test_fi_14_ephemeral_cleanup.py
│   │   ├── test_fi_15_ephemeral_loss.py
│   │   ├── test_fi_16_migration_rebuild.py
│   │   ├── test_fi_17_readiness_truthfulness.py
│   │   ├── test_fi_18_event_stream_reconnect.py
│   │   ├── test_fi_19_cancellation_execution.py
│   │   └── test_fi_20_e2e_destructive.py
│   ├── fixtures/
│   │   ├── blueprint/
│   │   │   ├── invalid_aspect_ratio_blueprint.json
│   │   │   ├── invalid_audio_asset_kind_blueprint.json
│   │   │   ├── invalid_audio_volume_blueprint.json
│   │   │   ├── invalid_duration_frames_blueprint.json
│   │   │   ├── invalid_fps_blueprint.json
│   │   │   ├── invalid_project_id_blueprint.json
│   │   │   ├── invalid_start_frame_blueprint.json
│   │   │   ├── invalid_transition_type_blueprint.json
│   │   │   ├── invalid_version_blueprint.json
│   │   │   ├── legacy_v1_blueprint.json
│   │   │   ├── missing_required_fields_blueprint.json
│   │   │   ├── valid_audio_plan_blueprint.json
│   │   │   ├── valid_minimal_blueprint.json
│   │   │   └── valid_multi_scene_blueprint.json
│   │   ├── canonical/
│   │   │   ├── 01_simple_text_scene.json
│   │   │   ├── 02_image_scene.json
│   │   │   ├── 03_video_scene.json
│   │   │   ├── 04_audio_plan.json
│   │   │   ├── 05_multi_scenes_effects_transitions.json
│   │   │   ├── 06_overrides_and_brand.json
│   │   │   ├── 07_aspect_1_1_non_30fps.json
│   │   │   ├── 08_aspect_9_16.json
│   │   │   ├── 09_timeline_basic.json
│   │   │   ├── 10_layer_stack.json
│   │   │   ├── 11_keyframes_linear.json
│   │   │   ├── 12_keyframes_easing.json
│   │   │   ├── 13_keyframes_spring.json
│   │   │   ├── 14_nested_groups.json
│   │   │   ├── 15_cross_scene_audio.json
│   │   │   ├── 16_transition_overlap.json
│   │   │   └── 17_60fps_animation.json
│   │   ├── clean_room_project/
│   │   │   ├── assets/
│   │   │   │   └── ready/
│   │   │   │       ├── audio/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   │       └── icons/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   └── 00_answers.md
│   │   ├── manifest/
│   │   │   ├── duplicate_id_manifest.json
│   │   │   ├── invalid_kind_manifest.json
│   │   │   ├── invalid_provenance_manifest.json
│   │   │   ├── invalid_status_manifest.json
│   │   │   ├── legacy_v1_ambiguous_manifest.json
│   │   │   ├── legacy_v1_valid_manifest.json
│   │   │   ├── project_id_mismatch_manifest.json
│   │   │   ├── unsupported_version_manifest.json
│   │   │   └── valid_manifest_v2.json
│   │   └── stt_parity/  [مجلد وسائط مستثناة أو فارغ]
│   ├── gates/
│   │   └── test_datastory_gate_contract.py
│   ├── generators/
│   │   ├── test_asset_resolution.py
│   │   └── test_scaffold.py
│   ├── golden_scenarios/
│   │   ├── test_concurrent_requests.py
│   │   ├── test_failure_recovery.py
│   │   ├── test_happy_path.py
│   │   └── test_migration_from_legacy.py
│   ├── metrics/
│   │   └── test_metrics.py
│   ├── performance/
│   │   ├── test_api_response_times.py
│   │   └── test_pipeline_performance.py
│   ├── remediation/
│   │   ├── reproductions/
│   │   │   ├── conftest.py
│   │   │   ├── test_asset_009_path_traversal.py
│   │   │   ├── test_conc_001_lost_update.py
│   │   │   ├── test_gate_001_facade_reproductions.py
│   │   │   ├── test_led_005_artifact_records_erasure.py
│   │   │   ├── test_led_008_corrupt_state.py
│   │   │   ├── test_led_019_approval_bypass.py
│   │   │   ├── test_led_022_skip_strict_qc.py
│   │   │   ├── test_led_054_props_divergence.py
│   │   │   ├── test_led_088_authority_duplication.py
│   │   │   ├── test_led_090_downstream_invalidation.py
│   │   │   ├── test_rec_001_recovery_empty_evidence.py
│   │   │   ├── test_s11_manifest_v2_reproductions.py
│   │   │   ├── test_s11_remediation_proof.py
│   │   │   ├── test_s12_blueprint_remediation_proof.py
│   │   │   ├── test_s12_blueprint_reproductions.py
│   │   │   ├── test_s13_remediation_proof.py
│   │   │   ├── test_s13_reproductions.py
│   │   │   ├── test_s14_remediation_proof.py
│   │   │   ├── test_s14_reproductions.py
│   │   │   ├── test_s15_remediation_proof.py
│   │   │   ├── test_s15_reproductions.py
│   │   │   ├── test_s16_remediation_proof.py
│   │   │   ├── test_s17_remediation_proof.py
│   │   │   ├── test_s18_remediation_proof.py
│   │   │   ├── test_s18_reproductions.py
│   │   │   ├── test_s19_remediation_proof.py
│   │   │   ├── test_s19_reproductions.py
│   │   │   ├── test_s20_remediation_proof.py
│   │   │   ├── test_s20_reproductions.py
│   │   │   ├── test_s21_remediation_proof.py
│   │   │   ├── test_s21_reproductions.py
│   │   │   ├── test_s22_remediation_proof.py
│   │   │   ├── test_s22_reproductions.py
│   │   │   ├── test_s23_remediation_proof.py
│   │   │   ├── test_s23_reproductions.py
│   │   │   ├── test_s24_remediation_proof.py
│   │   │   ├── test_s24_reproductions.py
│   │   │   └── test_state_001_lifecycle_bypass.py
│   │   └── s02_acceptance/
│   │       ├── conftest.py
│   │       ├── test_acc_001_unauthenticated_sensitive_request.py
│   │       ├── test_acc_002_approved_by_untrusted.py
│   │       ├── test_acc_003_project_scope_isolation.py
│   │       ├── test_acc_004_non_reviewer_approval.py
│   │       ├── test_acc_005_path_traversal.py
│   │       ├── test_acc_006_symlink_escape.py
│   │       ├── test_acc_007_docker_subcommand_validation.py
│   │       ├── test_acc_008_dangerous_subprocess_flags.py
│   │       ├── test_acc_009_skip_strict_qc_production.py
│   │       ├── test_acc_010_agy_is_managed_approval.py
│   │       └── test_acc_011_python_interpreter_contract.py
│   ├── remotion/
│   │   ├── ai_contracts_parity.test.ts
│   │   ├── asset_resolution.test.ts
│   │   ├── blueprint.test.ts
│   │   ├── capability_contracts_parity.test.ts
│   │   ├── conformance.test.ts
│   │   ├── contracts.test.ts
│   │   ├── creative_contracts_parity.test.ts
│   │   ├── datastory_contract.test.ts
│   │   ├── effects.test.ts
│   │   ├── manifest.test.ts
│   │   ├── merge.test.ts
│   │   ├── registry.test.ts
│   │   ├── s16_pre_mount_gate.test.ts
│   │   ├── s16_reproductions.test.ts
│   │   ├── s17_render_input_parity.test.ts
│   │   ├── s28_06_render_smoke.test.ts
│   │   ├── s28_r02_canonical_parity.test.ts
│   │   ├── s28_r02_red_tests.test.ts
│   │   ├── s28_r03_canonical_parity.test.ts
│   │   ├── s28_r03_red_tests.test.ts
│   │   ├── s28_r04_editor_performance.test.ts
│   │   ├── s28_r04_editor_session.test.ts
│   │   ├── s28_r04_mutations_core.test.ts
│   │   ├── s28_r04_subprocess_isolation.test.ts
│   │   ├── s28_r05_red_tests.test.ts
│   │   ├── s28_r05_subprocess_isolation.test.ts
│   │   ├── s28_r05_template_migration.test.ts
│   │   ├── s28_r05_template_spec.test.ts
│   │   ├── s28_r06_preview_core.test.ts
│   │   ├── s28_r06_preview_performance.test.ts
│   │   ├── s28_r06_templates_and_mutations.test.ts
│   │   ├── s28_r07_audio_core.test.ts
│   │   ├── s28_r07_audio_performance.test.ts
│   │   ├── s28_r07_critical_integration.test.ts
│   │   ├── s28_r07_waveform.test.ts
│   │   ├── s28_r07b_critical_integration.test.ts
│   │   ├── s28_r07b_performance.test.ts
│   │   ├── s28_r07b_preview_fidelity_and_proxy.test.ts
│   │   ├── s28_r08_renderer_core.test.ts
│   │   ├── s28_r09_remotion_adapter.test.ts
│   │   ├── s28_r10_canvas_adapter.test.ts
│   │   ├── s28_r11_master_compositor.test.ts
│   │   ├── s28_r12_render_planner.test.ts
│   │   ├── s28_r13_unified_authoring.test.ts
│   │   ├── s28_r14_production_integration.test.ts
│   │   ├── s28_r15_destruction_and_load.test.ts
│   │   ├── s28_r15_part3_final_campaigns.test.ts
│   │   ├── template_contract_parity.test.ts
│   │   └── template_runtime_resolution.test.ts
│   ├── security/
│   │   ├── test_guardian.py
│   │   ├── test_guardrails.py
│   │   ├── test_mcp_security.py
│   │   ├── test_path_traversal.py
│   │   ├── test_race_conditions.py
│   │   ├── test_s02_negative_enforcement.py
│   │   ├── test_security_path_traversal.py
│   │   ├── test_subprocess_security.py
│   │   └── test_tenant_authorization.py
│   ├── snapshots/
│   │   ├── command_guard_block_curl.json
│   │   ├── command_guard_block_npm_studio.json
│   │   ├── test_snapshots.py
│   │   ├── write_guard_block_absolute_path.json
│   │   ├── write_guard_block_studio_approved.json
│   │   └── write_guard_block_timings.json
│   ├── validators/
│   │   ├── test_schemas_validation.py
│   │   └── test_template_registry_consistency.py
│   └── conftest.py
├── التعلم/
│   ├── الاصلاح/
│   │   ├── Master_Remediation_Ledger_motion_محدث_S24_5.xlsx
│   │   ├── اخطاء.md
│   │   ├── الاخطاء_محدثة_بعد_S24_5.md
│   │   ├── خارطة_طريق_الإصلاح_حتى_الجاهزية_للإنتاج_محدثة_بعد_S24_5.md
│   │   └── خطة_الS27.md
│   └── التقارير/
│       ├── CODE_VERIFIED_PIPELINE_AND_STATE_MACHINE.md
│       ├── CODE_VERIFIED_RENDERING_SUBSYSTEM.md
│       └── LEVEL 0 — System Overview.md
├── .blueprint_lock.json
├── .dockerignore
├── .env
├── .env.example
├── .gitignore
├── .gitmodules
├── .trivyignore
├── hooks.json
├── LICENSE
├── package-lock.json
├── package.json
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── skills-lock.json
├── tsconfig.json
├── uv.lock
└── vitest.config.ts
```
