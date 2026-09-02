# Scene 1 Plan

**تم قراءة الملفات التالية قبل التنفيذ:**
- `references/deep/motion-taste/director/motion-personality.md`
- `references/deep/motion-taste/director/emotion-mapping.md`
- `references/deep/motion-taste/director/choreography.md`
- `references/deep/motion-taste/reference/timing-easing-tables.md`
- `ground-truth/TEMPLATE_INDEX.md`

## أ) التوقيتات:
- **حدود المشهد:** 0.05s إلى 4.97s
- **المدة الكلية:** 4.92 ثانية

## ب) مصفوفة اللقطات (shots[]):
1. **اللقطة الأولى (0.05s):**
   - **نمط الإطار:** Hero Object (Phone Frame)
   - **حركة الكاميرا:** Zoom In خفيف من مسافة بعيدة ليستقر الموبايل في المنتصف.
   - **الميديا المطلوبة:** قالب `phone-frame`، صوت ظهور `sfx_whoosh`.
   - **الإيماءة البصرية:** الموبايل يندفع بقوة (Overshoot 15-30%) مع بداية نطق كلمة "الموبايل" بـ Lock دقيق.
   - **الانتقال:** استمرار التركيز.

2. **اللقطة الثانية (1.63s):**
   - **نمط الإطار:** Typography Emphasis
   - **حركة الكاميرا:** ثابتة مع تركيز على الكابشن.
   - **الميديا المطلوبة:** كابشن `Trackingin` لكلمة "أقوى".
   - **الإيماءة البصرية:** تكبير الكلمة بشكل مفاجئ (Pop) عند نطق "أقوى" (1.63s) لدعم الإيقاع الحماسي.
   - **الانتقال:** استمرار.

3. **اللقطة الثالثة (2.65s - 4.97s):**
   - **نمط الإطار:** Context Reveal
   - **حركة الكاميرا:** حركة Pan خفيفة أو Parallax.
   - **الميديا المطلوبة:** كابشن `Trackingin` لكلمات "كمبيوترات وكالة ناسا زمان".
   - **الإيماءة البصرية:** ظهور الكلمات بتتابع سريع يعكس قِدم التكنولوجيا القديمة وسرعة التكنولوجيا الحديثة.
   - **الانتقال:** `WhipPan` للانتقال السريع إلى المشهد الثاني.

## ج) قواعد التوقيع المطبقة:
- **Beat Density:** 3 إيماءات بصرية رئيسية خلال 4.92 ثانية، مما يخلق إيقاعاً ديناميكياً يتناسب مع قوة الجملة.
- **تنويع الإطار:** تركيز مبدئي على الكائن (Hero Object) ثم تركيز على قوة الكلمة (Typography).
- **Gestural Sync:** تزامن الانطلاقة (`sfx_whoosh`) مع كلمة "الموبايل"، وتزامن النبضة البصرية مع كلمة "أقوى".
- **Parallax Depth:** الموبايل والكابشن في المقدمة مع توظيف الخلفية (bg_ai) بحركة بطيئة.

## د) الإحالات:
- `motion_taste_citation`: Energetic / Dynamic - "Signature: large scale changes (50-150%), fast color transitions, bold edge entrances." (motion-personality.md:54)
- `shot_recipes`: Hero Reveal, Typography Pop.

---

✅ Creative Quality Gate Passed:
- التنوع: تم استخدام قالبين جديدين (`phone-frame`, `Trackingin`).
- الـ SFX: تم ربط إيماءة الدخول بـ `sfx_whoosh`.
- الكثافة: 3 عناصر بصرية (خلفية 사이بر، موبايل، كابشن متصل).
- التزامن: تم ضبط حركة الكلمات بالملي ثانية حسب التحليل.
