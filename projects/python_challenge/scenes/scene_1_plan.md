# خطة المشهد 1: الخطاف (The Hook)

> **تم قراءة الملفات التالية قبل التنفيذ:**
> 1. `references/deep/motion-taste/director/motion-personality.md`
> 2. `references/deep/motion-taste/director/emotion-mapping.md`
> 3. `references/deep/motion-taste/director/choreography.md`
> 4. `references/deep/motion-taste/reference/timing-easing-tables.md`
> 5. `references/deep/ground-truth/TEMPLATE_INDEX.md`

---

## 1. شرح المشهد
- **الوظيفة الإخراجية:** خطاف انتباه (Hook) عالي الطاقة والمفاجأة لشد المشاهد فوراً خلال أول 2.88 ثانية.
- **التوقيت:** من 0.00s إلى 2.88s (الإطارات 0 إلى 86 @ 30fps).
- **النص الصوتي:** "بدك تتقن بايثون بثلاثين يوم بس؟"
- **الشعور المطلوب (Emotion):** `Surprise / Impact` + `Excitement` مع انطلاقة حركية متفجرة.

---

## 2. القوالب المستخدمة
| القالب المعتمد | العائلة | الوظيفة في المشهد |
|---|---|---|
| `cinematic-title-intro` | Typography & Captions | دخول العنوان الرئيسي للخطاف بهيبة بصرية وتأثير سينمائي |
| `bounce-text` | Typography & Captions | نبض وانبثاق كلمة "30 يوم" و "بايثون" بنبضة مرنة ذات Overshoot |
| `particle-explosion` | VFX & Overlays | انفجار جسيمات ضوئية ملونة مع لحظة ظهور رقم "30 يوم" |
| `push-transition` | Transitions | دفع حركي سريع للانتقال للمشهد الثاني |

---

## 3. الميديا المستخدمة
| الأصل | النوع | المصدر | المسار |
|---|---|---|---|
| `python.svg` | SVG Vector | processed/icons | `processed/icons/python.svg` |
| `whoosh_norm.wav` | SFX Audio | processed/audio | `processed/audio/whoosh_norm.wav` |
| `pop_norm.wav` | SFX Audio | processed/audio | `processed/audio/pop_norm.wav` |
| `vo_normalized.wav` | Voiceover | processed/audio | `processed/audio/vo_normalized.wav` |
| `music_normalized.wav` | BGM Music | processed/audio | `processed/audio/music_normalized.wav` |

---

## 4. شخصية الحركة والتوقيتات
- **النمط الحركي:** `Energetic / Dynamic`
- **زمن الدخول (Entrance Duration):** 180ms (ما يعادل 5-6 إطارات)
- **معادلة الحركة (Easing):** `ease-out-expo` (تدرج حاد سريع مع استقرار سلس)
- **المرونة والارتداد (Overshoot):** 20% باستخدام Spring (Stiffness: 300, Damping: 18)
- **الترتيب الزمني للحركة (Choreography):**
  - **الإطار 0 - 15 (0.0s - 0.5s):** دخول شعار بايثون في المركز مع توسع دائري ناعم وتلاشي إشعاعي للخلفية.
  - **الإطار 18 - 40 (0.6s - 1.35s):** توهج أزرق/أصفر لشعار بايثون وظهور الكابشن المفتاحي: `بدك تتقن بايثون؟`.
  - **الإطار 41 - 70 (1.36s - 2.35s):** انبثاق بطاقة رقمية ضخمة `30 يوم` مع تأثير انفجار جزيئات ملونة (`particle-explosion`) وصوت `pop_norm.wav`.
  - **الإطار 72 - 86 (2.4s - 2.88s):** وميض كلمة `بس؟` مع اهتزاز تركيز خفيف ثم بدء حركة الدفع للمشهد التالي.

---

## 5. الدخول والخروج والانتقال
- **الدخول (Setup):** انبثاق شعار بايثون المركزي من المنتصف (Scale: 0.3 -> 1.05 -> 1.0) مع مؤثر Whoosh خاطف.
- **الحدث البصري الرئيسي (Action):** انبثاق شارة "30 يوم" المتوهجة بحجم بارز في قلب الشاشة لتثبيت الوعد في عقل المشاهد.
- **الخروج (Exit):** انزلاق سريع وتكبير للأمام مع `push-transition` لتمهيد المشهد 2 (الانطلاق من الصفر لسكربتات الذكاء الاصطناعي).
