# Avatar Insta Reel

## القاعدة المطلقة
كل الخطوات تمر عبر `scripts/pipeline.py`. لا توجد استثناءات.

## الخطوات
1. أنشئ مشروعاً جديداً: `python scripts/scaffold_project.py <project_id>`
2. اكتب الخطة في `master_plan.md` (أنت تكتبها بنفسك، لا تستخدم سكربت توليد).
3. اجمع الأصول في `02_asset_manifest.json`.
4. ابنِ المخطط في `05_blueprint.json`.
5. شغل المنسق: `python scripts/pipeline.py <project_id>`
6. انتظر حتى ينتهي المنسق. لا تشغل أي بوابة يدوياً.

## الأوامر المحظورة
- ❌ `python scripts/gates/probe_qc.py` (لا تشغل البوابات يدوياً)
- ❌ `python scripts/gates/asset_gate.py`
- ❌ `python scripts/gates/plan_gate.py`
- ❌ `python scripts/gates/taste_gate.py`
- ❌ أي أمر يتجاوز الـ `pipeline.py`
