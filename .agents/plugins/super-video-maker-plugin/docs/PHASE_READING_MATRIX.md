# 📚 مصفوفة القراءة حسب المرحلة

## القاعدة الذهبية
اقرأ **فقط** الملفات المذكورة في المرحلة الحالية.
لا تقرأ ملفات أخرى إلا إذا طلبها المستخدم صراحةً.

## المرحلة 0: تحليل الصوت
- `projects/<id>/04_timings.json` (بعد إنشائه)
- `projects/<id>/.session_state.json` (إذا كان موجوداً)

**لا تقرأ:** القوالب، مراجع الـ Motion Taste، ملفات المشاهد

## المرحلة 1: التخطيط
- `references/deep/motion-taste/director/motion-personality.md`
- `references/deep/motion-taste/director/emotion-mapping.md`
- `references/deep/motion-taste/director/choreography.md`
- `references/deep/motion-taste/director/SFX_BINDING_MATRIX.md`
- `references/deep/motion-taste/reference/timing-easing-tables.md`
- `ground-truth/TEMPLATE_INDEX.md`
- `projects/<id>/04_timings.json`

**لا تقرأ:** ملفات المشاهد القديمة، تقارير الـ QC

## المرحلة 2: بناء مشهد N
- `projects/<id>/scenes/scene_N_plan.md`
- `projects/<id>/06_build/src/compositions/Scene{N-1}.tsx` (إذا كان N > 1)
- `ground-truth/TEMPLATE_INDEX.md` (القسم المتعلق بالمشهد فقط)
- `references/deep/motion-taste/director/SFX_BINDING_MATRIX.md`

**لا تقرأ:** خطط المشاهد الأخرى، مراجع Motion Taste الكاملة

## المرحلة 3: معالجة الصوتيات
- `projects/<id>/04_timings.json`
- `references/deep/motion-taste/director/SFX_BINDING_MATRIX.md`
- `projects/<id>/02_asset_manifest.json`

**لا تقرأ:** القوالب، ملفات المشاهد

## المرحلة 4: المراجعة والـ QC
- `projects/<id>/smart_qc_report.json`
- `projects/<id>/06_build/src/compositions/SceneN.tsx` (المشهد المراجع فقط)
- `projects/<id>/.agent_alerts.md` (إن وجد)

**لا تقرأ:** خطط المشاهد، مراجع Motion Taste

## المرحلة 5: الرندر
- `projects/<id>/.session_state.json`
- `projects/<id>/.studio_unlocked`
- `projects/<id>/.studio_approved`

**لا تقرأ:** أي ملفات أخرى

## ⚠️ استثناءات
يمكن قراءة ملفات خارج المصفوفة في هذه الحالات فقط:
1. طلب صريح من المستخدم
2. ظهور خطأ يتطلب مراجعة ملف مرجعي
3. استكشاف مشكلة في قالب معين
