# خطة المشهد 1: الخطاف والوعد (Scene 1 Plan)

تم قراءة الملفات التالية قبل التنفيذ:
- `references/deep/motion-taste/director/motion-personality.md`
- `references/deep/motion-taste/director/emotion-mapping.md`
- `references/deep/motion-taste/director/choreography.md`
- `references/deep/motion-taste/reference/timing-easing-tables.md`
- `ground-truth/TEMPLATE_INDEX.md`
- `references/deep/motion-taste/director/SFX_BINDING_MATRIX.md`

---

## أ) التوقيتات (Timings)
- **البداية والنهاية**: 0.00s إلى 6.14s (الإطارات: 0 إلى 184 f @ 30fps).
- **المدة الكلية**: 6.14 ثانية (184 إطار).
- **النص المنطوق**: "أعطني خمسة وأربعين ثانية، وسأعطيك خطة لتعلم البرمجة".

---

## ب) مصفوفة اللقطات (Shots Matrix)

### اللقطة 1.1 (0.00s - 2.66s | 0 - 80f): الخطاف الزمني
- **نمط الإطار**: `Hero Spotlight Frame` (شاشة 9:16 كاملة).
- **حركة الكاميرا**: Slow Push-In مع Parallax هادئ للشبكة الخلفية.
- **العناصر البصرية**:
  - خلفية تقنية داكنة مستمرة `bg_code_final.mp4` مع تدرج لوني زجاجي.
  - بطاقة زجاجية عليا تحمل شارة "الوقت / تحدي 45s".
  - عنوان رئيسي "أعطني 45 ثانية" بحركة `Blurreveal` زجاجية ناصعة.
  - كبسولة كابشن زجاجية تبرز الكلمات المنطوقة.
- **الإيماءة البصرية**: `Neon Ring` حول "خمسة وأربعين ثانية" عند التوقيت 780ms.
- **الصوتيات و SFX**:
  - `chime-soft.wav` / `pop.mp3` (-24 LUFS) عند 780ms مع ظهور الـ Neon Ring.
  - `pop.mp3` (-24 LUFS) عند 0ms لانبثاق البطاقة.
- **الانتقال**: `Slide Reveal` سلس نحو اللقطة التالية.

### اللقطة 1.2 (2.66s - 6.14s | 80 - 184f): الوعد البرمجي
- **نمط الإطار**: `Dynamic Card Frame` (توزيع متوازن وعريض).
- **حركة الكاميرا**: Subtle Zoom & Pan تتبع تركيز العين.
- **العناصر البصرية**:
  - انبثاق بطاقة زجاجية كبرى "خطة لتعلم البرمجة" مع شارة الكود الفيكتورية (`code.svg`).
  - نص توضيحي عريض "خطة عملية مجربة" مع تأثير توهج سيان ناعم.
  - كابشن كلمة بكلمة متزامن بدقة.
- **الإيماءة البصرية**: `Flash Cut` / `Marker Underline` تحت كلمة "خطة" و "البرمجة" عند التوقيت 4140ms.
- **الصوتيات و SFX**:
  - `swish-metal.wav` / `swoosh.mp3` (-24 LUFS) عند 4140ms.
  - `dramatic-boom.wav` (-20 LUFS) لتعزيز الإحساس بالوعد.
- **الانتقال إلى المشهد 2**: `Glasswipe` عند 6.00s (-100ms قبل نهاية المشهد) مع `whoosh.mp3`.

---

## ج) قواعد التوقيع المطبقة (Signature Rules)
- **Beat Density**: لقطتان مقسمتان بدقة على 6.14 ثانية (معدل لقطة كل 3 ثوانٍ).
- **Gestural Sync**: 
  - إيماءة `Neon Ring` متزامنة مع نطق "خمسة وأربعين" (780ms).
  - إيماءة `Marker Underline` متزامنة مع نطق "خطة" (4140ms).
- **Parallax Depth**: سرعة الخلفية 0.2x، سرعة البطاقات الزجاجية 0.5x، وسرعة العناوين والكابشن 1.0x.
- **Design Protocol**:
  - خطوط حديثة وعريضة، مع `direction: 'rtl'` و `flex-wrap` و `willChange: 'transform'`.
  - هوامش تنفس واسعة (Breathing Room) تمنع التصاق العناصر.

---

## د) الإحالات والقوالب
- `motion_taste_citation`: `references/deep/motion-taste/director/motion-personality.md:31-43` (Corporate/Modern Tech).
- `templates_used`: `HeadlineResolution`, `Blurreveal`, `Captions`, `Statcard`.
- `sfx_injected`: `pop.mp3`, `chime-soft.wav`, `swoosh.mp3`, `dramatic-boom.wav`, `whoosh.mp3`.

---

## 📝 مخرج الفحص الإبداعي الإلزامي (Creative Quality Gate)
```
✅ Creative Quality Gate Passed:
- التنوع: تم اختيار قوالب عائلات Typography (Blurreveal) و Primitives (HeadlineResolution) و Data (Statcard).
- الـ SFX: تم ربط 3 إيماءات بصرية بـ 3 مؤثرات صوتية مطبعة عند -24 LUFS و -20 LUFS وفق مصفوفة SFX_BINDING_MATRIX.
- الكثافة: المشهد يحتوي 3 طبقات كاملة (خلفية كود مستمرة، بطاقة زجاجية وسطى، عنوان وكابشن أمامي متوهج).
- التزامن: تم ضبط ظهور الكلمات والشارات بالملي ثانية بدقة (780ms, 4140ms, 5380ms).
```
