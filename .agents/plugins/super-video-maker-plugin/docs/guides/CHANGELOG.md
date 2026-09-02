# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-08-25

### Added
- Initial release of Super Video Maker Plugin
- 81 Remotion templates across 7 categories
- 64 cinematic engine components
- 7 MCP servers for audio, media, video, image, cache, FFmpeg, and editing
- 19 Python tools for video production pipeline
- 17 production recipes
- 12 reference playbooks
- Agent Plugins Spec v1.0.0 compliance
- Complete path rewriting with ${PLUGIN_ROOT}/${PLUGIN_DATA}
- TypeScript compilation with 0 errors

### Changed
- Converted from workspace skill to standalone plugin
- Updated all paths to use plugin-relative references
- Consolidated environment variables into single .env.example

### Fixed
- Template sync issues with Remotion
- MCP server import errors
- Path resolution in Python tools

## [Unreleased] - 2026-08-28
### Added
- Integrated premium 2026 component libraries into premium-templates/ as the primary layer of templates.
- Added Onda (kinetic typography & transitions), RemotionUI (social clips), Snapcn (text reveals), and Remocn (skills).
- Updated scripts/validate_blueprint.py to recognize the new path.
- Updated scripts/sync_templates.py to sync nested structures properly and inject them into TEMPLATE_INDEX.md as priority #1.
### Changed
- Performed RTL normalization on selected test components (WordStagger.tsx, 	ext-reveal.tsx, social-clip/index.tsx) enforcing Arabic typography (Cairo, Tajawal), right-to-left flex wrapping, and willChange: transform to prevent sub-pixel issues.
- Fixed 
emotion-template/src/Root.tsx to include the test compositions.


- Fixed omission: Fetched 4 specific components from remocn (whip-pan, blur-out-up, typewriter, caret) and 2 from remotion-bits (CardStack, Carousel3D) into premium-templates layer.
- Fixed omission: Updated VOCAB_REMAP.md to redirect aliases to the newly integrated premium templates.


- Deferred: Uninstalled 'remotion-animate-text' and 'remotion-subtitle' from package.json as they are currently unused dependencies. They are deferred to the upcoming caption improvement phase.


- ?????: ??? ?????? ????? ?????? snapcn ???? ????? snapcn.dev/r/ ???? ??? 404 ????? ????????. ??????? ????? ??????.

## [2026-08-29] توحيد المهارات والتوجيه (المرحلة 4.8)
- .agents/skills/ أصبح Junction إلى skills/ في الـ Plugin (مصدر مهارات واحد)
- AGENTS.md: دورة حياة الأصول + الراوتر أولاً + engine/ بدل cinematic-engine/
- video-production-protocol.md: الفهارس تشير إلى ground-truth/ الموحد
- skills/INDEX.md: شرح بنية المهارات وأدوارها (INDEX فهرس وليس مهارة)
- plugin.json: وصف محدث بالأرقام الحالية

## [2026-08-28] توحيد الأسماء (المرحلة 4.6)
- ARCHITECTURE_NEW.md → ARCHITECTURE.md الرسمي؛ القديم مؤرشف في references/deep/legacy/ARCHITECTURE_v1.md
- hyperframes-template: أُرشف بعد إثبات عدم الإشارة إليه
- remotion-template → remotion-app لفك الالتباس مع templates/
- تحديث project_full_overview.md ليعكس البنية الحالية

## [2026-08-28] إعادة الهيكلة النهائية (المرحلة 4.5)
- حذف المجلدات القديمة الفارغة: templates/, premium-templates/, cinematic-engine/, reference/, references/deep/ground-truth/
- إعادة تسمية templates-new/ إلى templates/
- تحديث كل السكريبتات وملفات التوجيه للمسارات الجديدة
- البنية النهائية: templates/ (مصدر الحقيقة) + engine/ (المحرك) + vendor/ (خارجي) + ground-truth/ (فهارس)

## [2026-08-28] توحيد الأسماء (المرحلة 4.6)
- ARCHITECTURE_NEW.md أصبح ARCHITECTURE.md الرسمي؛ القديم مؤرشف في references/deep/legacy/ARCHITECTURE_v1.md
- hyperframes-template: حُذف/أُرشف بعد إثبات عدم الإشارة إليه (أُرشِف نظراً لوجود 17 إشارة)
- remotion-template -> remotion-app لفك الالتباس مع templates/ (مكتبة القوالب)

## [2026-08-28] قانون الأصول (المرحلة 4.7)
- دورة حياة واحدة: incoming → cache → processing → ready
- دمج processed/ و storage/ في assets/ready/ وإلغاؤهما
- ASSET_INDEX.json مولّد آلياً (build_asset_index.py)
- asset_gate.py: يرفض الجلب من النت إذا وُجد أصل معالج مطابق
- تحديث check_cache/save_to_cache للمسارات الجديدة

- مهارات الـ vendor (remocn/snapcn) تعيش هنا فقط. مجلد .agents/skills في جذر مساحة العمل مُلغى؛ إن أعادت أي أداة إنشاءه، انقل محتواه إلى هنا واحذفه.
