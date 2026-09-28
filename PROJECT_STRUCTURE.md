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
│   │       ├── .agents/
│   │       │   └── mcp_state/  [مجلد وسائط مستثناة أو فارغ]
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
│   │       │   │   │   ├── assets/
│   │       │   │   │   │   └── downloads/
│   │       │   │   │   │       ├── coding_keyboard.mp4/  [مجلد وسائط مستثناة أو فارغ]
│   │       │   │   │   │       └── coding_keyboard_v2.mp4/  [مجلد وسائط مستثناة أو فارغ]
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
├── api/
│   ├── core/
│   │   └── errors.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── blueprint.py
│   │   ├── brand.py
│   │   ├── gates.py
│   │   ├── projects.py
│   │   └── render.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── blueprint.py
│   │   ├── gate.py
│   │   ├── project.py
│   │   └── responses.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gate_service.py
│   │   ├── pipeline_service.py
│   │   ├── render_service.py
│   │   └── scaffold_service.py
│   ├── __init__.py
│   ├── main.py
│   ├── README.md
│   └── websocket.py
├── assets/
│   ├── cache/
│   │   └── .gitkeep
│   ├── incoming/
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
├── config/
│   ├── violations_config.json
│   └── violations_config.schema.json
├── contracts/
│   ├── animations.ts
│   ├── blueprint.ts
│   ├── brand.ts
│   ├── fonts.ts
│   ├── override-validator.ts
│   ├── positions.ts
│   ├── SceneContent.ts
│   └── StyleSurface.ts
├── documentation/
│   ├── architecture/
│   │   └── ARCHITECTURE_TRUTH.md
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
│   │   ├── CONFLICTS.md
│   │   ├── DECISIONS.md
│   │   ├── EDGE_CASES_REPORT.md
│   │   ├── FINAL_AUDIT_REPORT.md
│   │   ├── FINAL_CHECKLIST.md
│   │   ├── HEALTH.md
│   │   ├── INTEGRATION_TEST_REPORT.md
│   │   ├── INVENTORY.md
│   │   ├── PROJECT_AUDIT_REPORT.md
│   │   ├── SYSTEM_HEALTH_REPORT.md
│   │   ├── TEMPLATE_DISCOVERY.md
│   │   └── TOOL_USAGE_AUDIT.md
│   ├── governance/
│   │   ├── ARCHITECTURE_CHANGE_CONTROL.md
│   │   ├── CHANGE_POLICY.md
│   │   ├── DEFECT_POLICY.md
│   │   └── DEPENDENCY_POLICY.md
│   ├── guides/
│   │   ├── DATA_DRIVEN_MIGRATION.md
│   │   ├── SECURITY_PATCH_NOTES.md
│   │   └── UPGRADE_NOTES.md
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
│   ├── template-aliases.ts
│   ├── template-registry.tsx
│   ├── tier-map.json
│   └── types.ts
├── remotion-app/
│   ├── .agents/
│   │   └── skills/  [مجلد وسائط مستثناة أو فارغ]
│   ├── .claude/
│   │   └── skills/
│   │       └── remotionui-agent/
│   │           └── SKILL.md
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
│   │   │   ├── music/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   ├── sfx/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   ├── video/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   └── vo/  [مجلد وسائط مستثناة أو فارغ]
│   │   └── render-props.json
│   ├── src/
│   │   ├── __tests__/
│   │   │   └── merge.test.ts
│   │   ├── components/
│   │   │   └── snap-cn/  [مجلد وسائط مستثناة أو فارغ]
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
│   │   │   └── state.ts
│   │   ├── BlueprintVideo.tsx
│   │   ├── captionLayout.ts
│   │   ├── CursorInteractionContext.tsx
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
│   ├── core/
│   │   ├── __init__.py
│   │   ├── e2e_data_render.py
│   │   ├── failure_injection.py
│   │   ├── failure_model.py
│   │   ├── recovery_engine.py
│   │   ├── retry_policy.py
│   │   ├── runtime_logger.py
│   │   ├── session_manager.py
│   │   ├── state_model.py
│   │   └── state_store.py
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
│   │   ├── generate_schema.ts
│   │   ├── generate_template_aliases.py
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
│   ├── ci_run_all.py
│   ├── open_studio.py
│   ├── pipeline.py
│   ├── render_project.py
│   └── scaffold_project.py
├── templates/
│   ├── _deprecated/
│   │   ├── elements/
│   │   │   ├── captions/
│   │   │   │   └── captions/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   ├── code/
│   │   │   │   ├── code-block/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   │   ├── code-diff/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   │   └── terminal/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   ├── data/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   ├── typography/
│   │   │   │   ├── blur-reveal/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   │   ├── rgb-glitch-text/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   │   ├── tracking-in/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   │   ├── typewriter/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   │   └── word-stagger/  [مجلد وسائط مستثناة أو فارغ]
│   │   │   └── ui/
│   │   │       └── split-screen/  [مجلد وسائط مستثناة أو فارغ]
│   │   └── scenes/
│   │       └── product/
│   │           └── ken-burns/  [مجلد وسائط مستثناة أو فارغ]
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
│   ├── api/
│   │   ├── test_gates.py
│   │   ├── test_pipeline_service.py
│   │   ├── test_project_creation.py
│   │   ├── test_projects.py
│   │   └── test_render.py
│   ├── architecture/
│   │   ├── test_adapter_layer_rules.py
│   │   ├── test_architecture_guards.py
│   │   ├── test_import_restrictions.py
│   │   ├── test_no_parallel_pipeline.py
│   │   ├── test_plugin_architecture_boundary.py
│   │   ├── test_quarantine_isolation.py
│   │   └── test_state_file_integrity.py
│   ├── archive/
│   │   └── test_migrate_legacy.py
│   ├── contracts/
│   │   ├── test_pipeline_service_contract.py
│   │   └── test_state_schema.py
│   ├── core/
│   │   ├── test_failure_classification.py
│   │   ├── test_runtime_logger.py
│   │   ├── test_safe_retry.py
│   │   └── test_trace_identity.py
│   ├── documentation/
│   │   ├── test_agents_md_accuracy.py
│   │   ├── test_architecture_truth.py
│   │   └── test_references_validity.py
│   ├── e2e/
│   │   ├── test_pipeline_integration.py
│   │   ├── test_unified_pipeline.py
│   │   └── true_e2e_suite.py
│   ├── fixtures/
│   │   └── clean_room_project/
│   │       ├── assets/
│   │       │   ├── cache/  [مجلد وسائط مستثناة أو فارغ]
│   │       │   ├── incoming/
│   │       │   │   └── .vo_original_0d300042.analysis.json
│   │       │   └── ready/
│   │       │       ├── audio/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── icons/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       ├── video/  [مجلد وسائط مستثناة أو فارغ]
│   │       │       └── .vo_norm_954726a6.analysis.json
│   │       └── 00_answers.md
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
│   ├── remotion/
│   │   ├── conformance.test.ts
│   │   ├── contracts.test.ts
│   │   ├── datastory_contract.test.ts
│   │   ├── effects.test.ts
│   │   ├── merge.test.ts
│   │   ├── registry.test.ts
│   │   └── template_runtime_resolution.test.ts
│   ├── security/
│   │   ├── test_guardian.py
│   │   ├── test_guardrails.py
│   │   ├── test_mcp_security.py
│   │   ├── test_path_traversal.py
│   │   ├── test_race_conditions.py
│   │   ├── test_security_path_traversal.py
│   │   └── test_subprocess_security.py
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
│   ├── CODE_VERIFIED_PIPELINE_AND_STATE_MACHINE.md
│   ├── CODE_VERIFIED_RENDERING_SUBSYSTEM.md
│   └── LEVEL 0 — System Overview.md
├── .blueprint_lock.json
├── .env.example
├── .gitignore
├── .gitmodules
├── CODE_VERIFIED_RENDERING_SUBSYSTEM.md
├── hooks.json
├── LICENSE
├── package-lock.json
├── package.json
├── PROJECT_RECONNAISSANCE.md
├── README.md
├── requirements.txt
├── skills-lock.json
├── tsconfig.json
├── vitest.config.ts
└── اخطاء.md
```
