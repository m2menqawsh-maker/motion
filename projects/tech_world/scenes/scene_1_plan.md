# خطة المشهد 1 - مشروع Tech World

تم قراءة الملفات التالية قبل التنفيذ:
- `references/deep/motion-taste/director/motion-personality.md`
- `references/deep/motion-taste/director/emotion-mapping.md`
- `references/deep/motion-taste/director/choreography.md`
- `references/deep/motion-taste/reference/timing-easing-tables.md`
- `ground-truth/TEMPLATE_INDEX.md`
- `references/deep/motion-taste/director/SFX_BINDING_MATRIX.md`
- `references/deep/motion-taste/director/user-signature-style.md`

## أ) التوقيتات
- **الحدود**: من 0.0 ثانية إلى 5.86 ثانية (بناءً على 04_timings.json)
- **المدة الكلية**: 5.86 ثانية
- **النص**: "الموبايل اللي بيدك حالياً أقوى بآلاف المرات من الأجهزة اللي طلعت الإنسان للقمر"

## ب) مصفوفة اللقطات (shots[])

### اللقطة 1: 0.0 - 1.96 (المدة: 1.96 ث)
- **النص**: "الموبايل اللي بيدك حالياً"
- **نمط الإطار**: Full-Bleed (شاشة كاملة)
- **حركة الكاميرا**: Parallax (زوم بطيء للداخل - Deep Zoom)
- **الميديا المطلوبة**: مجسم هاتف واقعي (Phone Mockup) على خلفية بيضاء نظيفة.
- **الإيماءة البصرية**: Flash Cut مع أول ظهور للكلمة "الموبايل" (Word Lock: `الموبايل`).
  - **SFX**: `dramatic-boom.wav` (-20 LUFS) عند 0.0ms.
- **الانتقال**: Zoom Through (غوص داخل شاشة الهاتف) لتبدأ اللقطة الثانية.
  - **SFX**: `whoosh-deep.wav` (-24 LUFS) قبل الانتقال بـ 100ms.

### اللقطة 2: 1.96 - 5.86 (المدة: 3.90 ث)
- **النص**: "أقوى بآلاف المرات من الأجهزة اللي طلعت الإنسان للقمر"
- **نمط الإطار**: Square Framed Window (بداخل شاشة الهاتف المستهدفة من الغوص)
- **حركة الكاميرا**: ParallaxPan (حركة انسيابية للأعلى)
- **الميديا المطلوبة**: صورة أو فيديو يعبر عن الفضاء أو التكنولوجيا المعقدة (أجهزة قديمة أو قمر).
- **الإيماءة البصرية**: Neon Ring حول كلمة "بآلاف المرات" (Word Lock: `بآلاف`).
  - **SFX**: `chime-soft.wav` (-24 LUFS) عند توقيت ظهور الكلمة (2.66 ث).
- **الانتقال للمشهد التالي**: Whip Pan إلى المشهد 2 (شاشة منقسمة).
  - **SFX**: `whip-pan.wav` (-24 LUFS) في نهاية المشهد (5.86 ث).

## ج) قواعد التوقيع المطبقة
- **Beat Density (§0.3)**: الجملة 5.86 ثانية، تم تقسيمها إلى لقطتين لضمان استمرار الانتباه.
- **تنويع الإطار (§0.4)**: اللقطة الأولى Full-Bleed، اللقطة الثانية Square Framed Window.
- **Gestural Sync (§7)**: كل إيماءة مربوطة بصوت مباشر من مصفوفة الـ SFX.
- **Parallax Depth (§10)**: عمق بصري بتواجد الهاتف كعنصر أمامي، والخلفية تتحرك ببطء.

## د) الإحالات
- **treatment_citation**: `user-signature-style.md:18` (Word-Chase Zoom — زوم مطاردة الكلمة).
- **motion_taste_citation**: `motion-personality.md:28` (Premium: slow fades, subtle scale 98%→100%, ultra-smooth).
- **shot_recipes**: `ImageZoomReveal`, `KenBurns`

---
✅ **Creative Quality Gate Passed**:
- **التنوع**: [تم استخدام 2 قوالب (ImageZoomReveal، KenBurns) من عائلات مختلفة عن الصفر]
- **الـ SFX**: [تم ربط 2 إيماءة بصرية و 2 انتقالات بـ 4 مؤثرات صوتية (dramatic-boom, whoosh-deep, chime-soft, whip-pan)]
- **الكثافة**: [تم إضافة هاتف كعنصر Foreground، وفيديو فضاء كعنصر Midground، وإيماءة Neon Ring]
- **التزامن**: [تم ضبط التوقيتات بالملي ثانية حسب ملف 04_timings.json، مثلا الكلمة "بآلاف" عند 2.66s]
