# -*- coding: utf-8 -*-
"""stitch_skill.py — يخيط الملفات القديمة بالطبقات الجديدة (idempotent)."""
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent
R = DST / "reference"

FOOT = ("\n\n---\n> 🔗 **ضمن المهارة الموحدة:** يُوجَّه هذا الدفتر عبر `ROUTER.md` §4/§9، ويُفهرس في "
        "`reference/ground-truth/PLAYBOOKS_INDEX.md`؛ قوالبه من `reference/ground-truth/TEMPLATE_INDEX.md`، "
        "وذوقه من `reference/motion-taste/`، وعمقه من `reference/cinematic/layer-stack.md`، "
        "وقواعده التشغيلية في `reference/legacy/SKILL_51_RULES.md`.\n")

SKILL_SEC = """
## المصادر التشغيلية الكاملة
- القواعد التشغيلية الـ 51: `reference/legacy/SKILL_51_RULES.md` • المرجع القديم: `reference/legacy/REFERENCE_legacy.md`
- الدفاتر: `FFMPEG_PLAYBOOK.md` • `VIDEO_COPY_PLAYBOOK.md` • `SPOKEN_VO_HUMANIZER.md` • `HOOK_PLAYBOOK_ARTICLE_SPRINT.md` • `LIVING_CANVAS_PLAYBOOK.md` • `TABLETOP_EXPLAINER_PLAYBOOK.md` • `MOTION_COLLAGE_STYLE.md` • `HYPERREALISTIC_IMAGE_SOP.md` • `REVIEW_VIDEO_PLAYBOOK.md` • `SEEDANCE_AVATAR_ROI.md` • `REMOTION_VIDEO_GUIDE.md` • `WORKFLOW_EXAMPLES.md`
- التنفيذ والاختبار: `commands/` • `recipes/` • `tools/` • `workflows/` • `templates/` • `tests/` • `remotion-app/` • `references/deep/legacy/hyperframes-template/`
"""

ROUTER_SEC = """
## §9 ربط الدفاتر التشغيلية (Playbooks)
| الدفتر | متى يُقرأ |
|---|---|
| VIDEO_COPY_PLAYBOOK.md | قبل كتابة أي نص/سيناريو |
| SPOKEN_VO_HUMANIZER.md | تحويل نص مكتوب إلى VO منطوق |
| HOOK_PLAYBOOK_ARTICLE_SPRINT.md | صياغة الخطاف (أول 3 ثوانٍ) |
| FFMPEG_PLAYBOOK.md | أي عملية FFmpeg يدوية |
| REMOTION_VIDEO_GUIDE.md | الأرقام الرسمية لفيزياء النوابض والتوقيت |
| LIVING_CANVAS_PLAYBOOK.md | وصفة living-canvas-explainer |
| TABLETOP_EXPLAINER_PLAYBOOK.md | وصفة tabletop-levels-explainer |
| MOTION_COLLAGE_STYLE.md | وصفة motion-collage-explainer |
| HYPERREALISTIC_IMAGE_SOP.md | توليد شخصيات UGC واقعية |
| REVIEW_VIDEO_PLAYBOOK.md | وصفة review-conquest-compilation |
| SEEDANCE_AVATAR_ROI.md | قرارات أفاتار Seedance/HeyGen |
| WORKFLOW_EXAMPLES.md | أمثلة تنفيذية كاملة لخطوط الإنتاج |
"""

APPENDS = [
 (DST/"SKILL.md", "المصادر التشغيلية الكاملة", SKILL_SEC),
 (DST/"ROUTER.md", "§9 ربط الدفاتر", ROUTER_SEC),
 (R/"patterns"/"INDEX.md", "فض الاشتباك", """
## ⚖️ فض الاشتباك (أي ملف أقرأ؟)
- `transitions.md` هنا = أنماط توليد SaaS؛ قانون TransitionSeries الرسمي: `../remotion/markup/transitions.md`
- `sequencing.md` هنا = أنماط توليد؛ القانون: `../remotion/markup/sequencing.md`
- `3d.md` هنا = المرجع المعتمد لمشاهد 3D؛ أساس R3F: `../remotion/markup/3d.md`
- `spring-physics.md` = فهم فيزيائي؛ الأرقام الرسمية: `REMOTION_VIDEO_GUIDE.md` + `../motion-taste/reference/timing-easing-tables.md`
"""),
 (R/"ad-spine"/"INDEX.md", "فض الاشتباك", """
## ⚖️ فض الاشتباك
- `testimonial/quote-card.md` = مرجع تايبوغرافيا ودفعات؛ القالب الرسمي القابل للاستيراد: `../../templates/quote-card.tsx`
"""),
 (R/"cinematic"/"INDEX.md", "فض الاشتباك", """
## ⚖️ فض الاشتباك + الأصول
- المتداخل مع الـ81 (EndCard/CountUp/TypeWriter/Highlight/Pulse/ScenePush): الرسمي = `templates/`؛ نسخ cinematic فقط مع Window/app-ui في ديمو المنتج
- الأصول الصوتية: `assets/ready/sfx/` و `assets/ready/music/` (boom/impact/whoosh + click/notification/pop/typing + background)
"""),
 (R/"remotion"/"INDEX.md", "بقية القانون", """
## 🧭 بقية القانون (كانت يتيمة)
- `markup/compositions.md` + `markup/parameters.md` | تعريف التراكيب والباراميترات
- `markup/video-editing.md` + `markup/ffmpeg.md` | مونتاج كليبات مستقلة وFFmpeg داخل Remotion
- `markup/audio-visualization.md` | موجات ومحللات صوتية بصرية
- `markup/SKILL.md` + `create/SKILL.md` + `render/SKILL.md` + `multimedia/SKILL.md` + `studio/SKILL.md` | نقاط دخول الأقسام
- `create/tailwind.md` | Tailwind داخل Remotion
"""),
]

for path, marker, text in APPENDS:
    t = path.read_text(encoding="utf-8")
    if marker not in t:
        path.write_text(t.rstrip() + "\n" + text, encoding="utf-8")
        print("stitched:", path.relative_to(DST))

for pb in sorted(DST.glob("*.md")):
    if pb.name in {"SKILL.md", "ROUTER.md", "README.md", "AUDIT_REPORT.md"}: continue
    t = pb.read_text(encoding="utf-8")
    if "ضمن المهارة الموحدة" not in t:
        pb.write_text(t.rstrip() + FOOT, encoding="utf-8")
        print("footed:", pb.name)
print("STITCH DONE")
