# جرد شامل للمسارات المتوازية (INVENTORY)

## 1. شجرة المجلدات الفعلية (العمق 2)
- **`templates/` (root)**
  - (No subdirectories, contains files directly)
- **`engine/` (plugin)**
  - `audio/`, `camera/`, `choreography/`, `cursor/`, `layout/`, `primitives/`, `scenes/`, `ui-state/`
- **`ground-truth/` (plugin)**
  - `collections/`
- **`scripts/` (root)**
  - `gates/`
- **`tools/` (plugin)**
  - `mcp-servers/`
- **`api/` (root)**
  - `routers/`, `services/`
- **`schemas/` (root)**
  - `examples/`
- **`contracts/` (root)**
  - (Empty or no subdirectories)
- **`registry/` (root)**
  - `thumbs/`
- **`build/` (root)**
  - `fixtures/`, `src/`
- **`.agents/` (root)**
  - `guardian/`, `plugins/`, `project_templates/`, `rules/`

## 2. تحليل مجلد `templates/`
- **عدد الملفات الفعلي**: 32 ملفاً (منها 28 ملف `.tsx`).
- **عينة لـ 10 ملفات**: `AnnounceTitle.tsx`, `AnswerStream.tsx`, `applyOverride.ts`, `BlockWordmark.tsx`, `brand-resolver.ts`, `Caret.tsx`, `FollowerRush.tsx`, `HeroLaunch.tsx`, `Input.tsx`, `KaraokeCaptions.tsx`.
- **التشخيص الأخطر**: الملفات الموجودة هنا هي قوالب الـ 27 TSX (المسار ب - Data-Driven) بالإضافة إلى بعض ملفات المساعدة (`utils`)، ولا تحتوي على قوالب الـ 172 الخاصة بالـ Spec-Driven كما تفترض أدوات (المسار أ). **المجلد هو خليط غير متناسق مع الفهارس**.

## 3. تحليل مجلد `ground-truth/`
- **محتوى `CANONICAL_PATHS.json`**: يحتوي على 10 مفاتيح/مدخلات.
- **هل يخلط مسارين؟**: **نعم بشكل صريح**. يوجه كل من `unified` و `legacy` إلى `templates/`، مما يعزز الفوضى بين قوالب TSX والمصادر القديمة. كما أنه يوجه لـ `cinematic_engine` ومجلدات أخرى غير متطابقة هيكلياً مع الواقع.

## 4. قائمة وجود ملفات النظام والمتحكمات
**الملفات الموجودة فعلياً:**
- `spec_validator.py` (في الـ plugin)
- `scene_compiler.py` (في الـ plugin)
- `template_router.py` (في الـ plugin)
- `taste_gate.py` (في الـ plugin)
- `transcript_cleaner.py` (في الـ plugin)
- `build_ground_truth.py` (في الـ plugin)
- `vendor/` (مجلد، في الـ plugin)

**الملفات المفقودة (التي لا وجود لها):**
- `visual_match_gate.py` ❌
- `asset_gate.py` ❌
- `build_asset_index.py` ❌

## 5. قائمة الزوائد (Residuals)
**الزوائد الموجودة فعلياً:**
- `scripts_backup/` (موجودة في الـ plugin)
- `scratch/` (موجودة في الجذر)
- `plugin_tree*.txt` (موجود منها 3 ملفات في الـ plugin: `plugin_tree.txt`, `plugin_tree_clean.txt`, `plugin_tree_level2.txt`)
- `test_spec.json` (موجود في الـ plugin)
- `reference/` (موجود في الـ plugin، مفرد بدلاً من references)

**الزوائد المفقودة:**
- ملفات `phase_13..16_*.json` غير موجودة.
- عقود certification غير موجودة داخل `ground-truth/`.
