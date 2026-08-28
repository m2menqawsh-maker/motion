# خطة المشهد 3: المرحلة الأولى — الأساسيات (Days 1-10)

> **تم قراءة الملفات التالية قبل التنفيذ:**
> 1. `references/deep/motion-taste/director/motion-personality.md`
> 2. `references/deep/motion-taste/director/emotion-mapping.md`
> 3. `references/deep/motion-taste/director/choreography.md`
> 4. `references/deep/motion-taste/reference/timing-easing-tables.md`
> 5. `references/deep/ground-truth/TEMPLATE_INDEX.md`

---

## 1. شرح المشهد
- **الوظيفة الإخراجية:** عرض أول مرحلة عملية ملموسة (الأيام 1 إلى 10) وتفكيكها إلى 3 مفاهيم برمجية سهلة وسريعة مع إبراز بناء أول مشروع عملي (آلة حاسبة) في نفس اليوم.
- **التوقيت:** من 7.44s إلى 15.50s (الإطارات 223 إلى 465 @ 30fps = 242 إطاراً).
- **النص الصوتي الدقيق:** "أول عشر تيام بتتعلم الأساسيات: متغيرات، لوبات وآلة حاسبة كلها بنفس اليوم"
- **الشعور المطلوب (Emotion):** `Confidence + Clarity` (إزالة رهبة البدايات والشعور بالإنجاز السريع).

---

## 2. القوالب المستخدمة
| القالب المعتمد | العائلة | الوظيفة في المشهد |
|---|---|---|
| `progress-steps` | Data & Stats | بطاقة المرحلة الأولى "الأيام 1 - 10" مع مؤشر تقدم الخطوة 1/3 |
| `animated-list` | Typography & Captions | دخول متتابع للبطاقات الثلاث (المتغيرات، اللوبات، الآلة الحاسبة) |
| `popping-text` | Typography & Captions | نبضات حركية للكلمات المفتاحية وأيقونات البرمجة |
| `push-transition` | Transitions | دفع حركي للانتقال للمرحلة الثانية (الأيام 11-20) |

---

## 3. الميديا المستخدمة
| الأصل | النوع | المصدر | المسار |
|---|---|---|---|
| `calculator.svg` | SVG Vector | processed/icons | `processed/icons/calculator.svg` |
| `repeat.svg` | SVG Vector | processed/icons | `processed/icons/repeat.svg` |
| `code.svg` | SVG Vector | processed/icons | `processed/icons/code.svg` |
| `sfx_whoosh.wav` | SFX Audio | processed/audio | `processed/audio/whoosh_norm.wav` |
| `sfx_pop.wav` | SFX Audio | processed/audio | `processed/audio/pop_norm.wav` |
| `sfx_digital.wav` | SFX Audio | processed/audio | `processed/audio/digital_norm.wav` |
| `vo_normalized.wav` | Voiceover | processed/audio | `processed/audio/vo_normalized.wav` |
| `music_normalized.wav` | BGM Music | processed/audio | `processed/audio/music_normalized.wav` |

---

## 4. شخصية الحركة والتوقيتات
- **النمط الحركي:** `Energetic / Dynamic`
- **التتابع (Stagger Budget):** 100ms بين كل بطاقة فرعية (Stagger sequential).
- **السرعة والـ Easing:** `ease-out-expo` (دخول سريع 180ms مع Overshoot 15%).
- **الترتيب الزمني للحركة (Choreography):**
  - **الإطار 0 - 85 (7.44s - 10.28s):** انزلاق شارة "المرحلة 1: الأيام 1 - 10 (الأساسيات)" في أعلى الشاشة مع خط أزرق/سيان نيون.
  - **الإطار 85 - 127 (10.28s - 11.66s):** انبثاق بطاقة "1. المتغيرات Variables (x = 10)" مع أيقونة كود مشعة وصوت `pop_norm.wav`.
  - **الإطار 127 - 158 (11.66s - 12.72s):** انبثاق بطاقة "2. اللوبات Loops (for / while)" مع أيقونة `repeat.svg` الخضراء النيون تدور بديناميكية وصوت `pop_norm.wav`.
  - **الإطار 158 - 200 (12.72s - 14.10s):** انبثاق بطاقة "3. الآلة الحاسبة Calculator 🧮" البرتقالية والسيان المشعة `calculator.svg`.
  - **الإطار 200 - 242 (14.10s - 15.50s):** وميض شارة "كلها بنفس اليوم! ⚡" مع إضاءة ذهبية والانتقال للمرحلة التالية.

---

## 5. الدخول والخروج والانتقال
- **الدخول (Setup):** انزلاق سلس من اليمين لمتابعة نهاية المشهد 2.
- **الحدث البصري الرئيسي (Action):** تتابع البطاقات الثلاث المتدرجة للمفاهيم الأساسية لتشكيل لوحة تعليمية واضحة.
- **الخروج (Exit):** دفع حركي `push-transition` تمهيداً للأيام 11-20.
