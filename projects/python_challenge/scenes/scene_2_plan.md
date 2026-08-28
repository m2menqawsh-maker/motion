# خطة المشهد 2: الوعد الكبير والرحلة (The Big Promise)

> **تم قراءة الملفات التالية قبل التنفيذ:**
> 1. `references/deep/motion-taste/director/motion-personality.md`
> 2. `references/deep/motion-taste/director/emotion-mapping.md`
> 3. `references/deep/motion-taste/director/choreography.md`
> 4. `references/deep/motion-taste/reference/timing-easing-tables.md`
> 5. `references/deep/ground-truth/TEMPLATE_INDEX.md`

---

## 1. شرح المشهد
- **الوظيفة الإخراجية:** تجسيد الوعد التحويلي الكبير (من نقطة البداية الصفرية إلى بناء سكربتات ونماذج الذكاء الاصطناعي باليد) لبناء الثقة والحماس العالي.
- **التوقيت:** من 2.88s إلى 7.44s (الإطارات 86 إلى 223 @ 30fps = 137 إطاراً).
- **النص الصوتي الدقيق:** "من الصفر لآخر سكربت ذكاء اصطناعي بتبرمجه بإيدك!"
- **الشعور المطلوب (Emotion):** `Excitement + Growth / Achievement` (انتقال بصري ملموس من الصفر للقمة).

---

## 2. القوالب المستخدمة
| القالب المعتمد | العائلة | الوظيفة في المشهد |
|---|---|---|
| `progress-bars` | Data & Stats | خط تقدم نيون متصاعد ينطلق من 0% إلى 100% بسرعة فائقة |
| `card-flip` | Containers & Cards | بطاقة زجاجية ثلاثية الأبعاد مشعة تفتح لتكشف سكربت الذكاء الاصطناعي |
| `bubble-pop-text` | Typography & Captions | انبثاق كلمات "ذكاء اصطناعي" و "بإيدك!" مع هالة ضوئية وتأثير بوب |
| `slide-wipe` | Transitions | مسح انسيابي للانتقال لمرحلة الأيام (1-10) |

---

## 3. الميديا المستخدمة
| الأصل | النوع | المصدر | المسار |
|---|---|---|---|
| `brain.svg` | SVG Vector | processed/icons | `processed/icons/brain.svg` |
| `bot.svg` | SVG Vector | processed/icons | `processed/icons/bot.svg` |
| `sfx_whoosh.wav` | SFX Audio | processed/audio | `processed/audio/whoosh_norm.wav` |
| `sfx_pop.wav` | SFX Audio | processed/audio | `processed/audio/pop_norm.wav` |
| `sfx_digital.wav` | SFX Audio | processed/audio | `processed/audio/digital_norm.wav` |
| `vo_normalized.wav` | Voiceover | processed/audio | `processed/audio/vo_normalized.wav` |
| `music_normalized.wav` | BGM Music | processed/audio | `processed/audio/music_normalized.wav` |

---

## 4. شخصية الحركة والتوقيتات
- **النمط الحركي:** `Energetic / Dynamic`
- **السرعة والـ Easing:** `ease-out-expo` (دخول سريع 180ms مع استقرار مطاطي ناعم Overshoot 18%)
- **الترتيب الزمني للحركة (Choreography):**
  - **الإطار 86 - 110 (2.88s - 3.70s):** الخروج من نقطة علامة الاستفهام، ظهور دائرة "0 LEVEL: من الصفر" تنبثق بتأثير مرن وصوت `whoosh`.
  - **الإطار 111 - 148 (3.70s - 4.94s):** انطلاق شعاع شريط التقدم النيون بسرعة تصاعدية (0% -> 100%) متزامناً مع كلمة "لآخر سكربت".
  - **الإطار 148 - 188 (4.94s - 6.30s):** انبثاق بطاقة الذكاء الاصطناعي الزجاجية ثلاثية الأبعاد (AI Script Card) بتوهج سيان/بنفسجي مع أيقونة الدماغ المشعة `brain.svg` وأسطر كود شبكة عصبية مضيئة وصوت `digital_norm.wav`.
  - **الإطار 189 - 223 (6.30s - 7.44s):** ظهور شارة التأكيد "بتبرمجه بإيدك! ⚡" مع نبض ضوئي واستقرار المشهد تمهيداً للانتقال إلى المرحلة الأولى (الأيام 1-10).

---

## 5. الدخول والخروج والانتقال
- **الدخول (Setup):** انبثاق نقطة الصفر من قلب نقطة علامة الاستفهام في المشهد السابق.
- **الحدث البصري الرئيسي (Action):** صعود شريط التقدم وانفجار بطاقة سكربت الذكاء الاصطناعي الزجاجية.
- **الخروج (Exit):** انزلاق سلس `slide-wipe` للانتقال للمشهد الثالث.
