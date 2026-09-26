import os
from pathlib import Path

root = Path(r"c:\video\clean-video-workspace")
output_path = root / "PROJECT_STRUCTURE.md"

media_exts = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"
}

ignored_dirs_anywhere = {
    ".git", ".venv", ".pytest_cache", ".remediation", "logs", "scratch",
    "__pycache__", ".vite", ".vite-temp"
}

template_pkgs = {"remotion-bits", "remotion-ui"}

def format_tree(dir_path: Path, prefix=""):
    lines = []
    try:
        raw_entries = list(dir_path.iterdir())
    except Exception:
        return lines

    filtered = []
    for e in raw_entries:
        name = e.name
        name_lower = name.lower()
        rel = e.relative_to(root).as_posix()
        
        if name_lower.endswith(".pyc") or name_lower.endswith(".map"):
            continue
            
        if e.is_dir() and name_lower in ignored_dirs_anywhere:
            continue
            
        # Exclude experimental projects
        if rel in ("projects", "remotion-app/projects"):
            filtered.append((e, "[مجلد المشاريع التجريبية - مستثنى مئات مجلدات prj_* و test-*]"))
            continue
        if rel.startswith("projects/") or rel.startswith("remotion-app/projects/"):
            continue
        if "public/projects" in rel:
            continue
            
        # node_modules special handling
        if e.name == "node_modules":
            parent_parts_lower = [p.lower() for p in e.parent.parts]
            if any(tp in parent_parts_lower for tp in template_pkgs):
                continue
            has_templates = any((e / tp).exists() for tp in template_pkgs)
            if not has_templates:
                continue
            filtered.append((e, "[مكتبات npm العامة مستثناة، مقتصر على مكتبات القوالب أدناه]"))
            continue
            
        # Inside node_modules:
        if dir_path.name == "node_modules":
            if name_lower not in template_pkgs:
                continue
                
        # Media filtering:
        if not e.is_dir() and e.suffix.lower() in media_exts:
            continue
            
        filtered.append((e, None))
        
    filtered.sort(key=lambda item: (not item[0].is_dir(), item[0].name.lower()))
    
    for i, (entry, note) in enumerate(filtered):
        is_last = (i == len(filtered) - 1)
        connector = "└── " if is_last else "├── "
        sub_prefix = "    " if is_last else "│   "
        
        if entry.is_dir():
            if note:
                lines.append(f"{prefix}{connector}{entry.name}/  {note}")
                if entry.name == "node_modules":
                    sub_lines = format_tree(entry, prefix + sub_prefix)
                    lines.extend(sub_lines)
            else:
                sub_lines = format_tree(entry, prefix + sub_prefix)
                if not sub_lines:
                    lines.append(f"{prefix}{connector}{entry.name}/  [مجلد وسائط مستثناة أو فارغ]")
                else:
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    lines.extend(sub_lines)
        else:
            lines.append(f"{prefix}{connector}{entry.name}")
            
    return lines

def main():
    tree_lines = format_tree(root)

    header = """# شجرة ملفات مشروع Clean Video Workspace

> **تاريخ التوليد:** 2026-09-18  
> **مسار جذر المشروع:** `c:\\video\\clean-video-workspace`  
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
"""

    footer = """```
"""

    full_content = header + "\n".join(tree_lines) + "\n" + footer
    output_path.write_text(full_content, encoding="utf-8")
    print(f"Successfully generated {output_path} with {len(tree_lines)} tree lines.")

if __name__ == "__main__":
    main()
