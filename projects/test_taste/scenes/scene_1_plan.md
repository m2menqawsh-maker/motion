# خطة المشهد 1 (الهوك)

تم قراءة الملفات التالية قبل التنفيذ: 
`motion-personality.md`, `emotion-mapping.md`, `choreography.md`, `timing-easing-tables.md`, `user-signature-style.md`

## أ) التوقيتات
- **الحدود**: من 0.02 إلى 2.66 ثانية (بناءً على `split_voiceover_sentences`).
- **المدة الكلية**: 2.64 ثانية.
- **النص**: "أعطني خمسة واربعين ثانية"

## ب) مصفوفة اللقطات (shots[])

### اللقطة 1: 0.02 - 0.78s ("أعطني")
- **نمط الإطار**: Full-Bleed (خلفية سايبربانك متحركة بالكامل).
- **حركة الكاميرا**: دخول سريع بـ Whip Pan، مع زوم بسيط للداخل.
- **الميديا المطلوبة**: `bg_neon_2_intra.mp4` كخلفية.
- **الإيماءة البصرية**: كلمة "أعطني" تظهر بـ Flash Cut لشد الانتباه الفوري (مربوطة بـ word_index 0).
- **الانتقال**: Graphic Match (تكبير سريع للكلمة لتتحول للقطة التالية).

### اللقطة 2: 0.78 - 2.66s ("خمسة واربعين ثانية")
- **نمط الإطار**: Dynamic Typography (نص ساطع ضخم يملأ الشاشة).
- **حركة الكاميرا**: Word-Chase Zoom (تتبع سريع واندفاع نحو كلمتي "خمسة واربعين" بحركة ease-out-expo).
- **الميديا المطلوبة**: المؤثر الصوتي `swoosh_norm.wav` لحظة الاندفاع.
- **الإيماءة البصرية**: Neon Ring (دائرة نيون) تظهر حول رقم "45" للتأكيد على الوعد الزمني (مقفولة على word "خمسة واربعين").
- **الانتقال**: Whip Pan للانتقال إلى المشهد التالي.

## ج) قواعد التوقيع المطبقة
- **Beat Density (§0.3)**: مدة 2.64 ثانية ← تخصيص لقطتين (سريعة ثم أطول).
- **تنويع الإطار (§0.4)**: انتقال من Full-Bleed (خلفية واضحة) إلى Dynamic Typography (تركيز على النص).
- **Gestural Sync (§7)**: إيماءة Neon Ring حول "45" تتزامن مع مؤثر `swoosh_norm.wav`.
- **Parallax Depth (§10)**: عمق 2.5D في اللقطة الثانية (النص الأمامي يتحرك أسرع من خطوط الخلفية).

## د) الإحالات
- **treatment_citation**: `user-signature-style.md:18` (Word-Chase Zoom مقفول على الكلمة).
- **motion_taste_citation**: `motion-personality.md:54` (Energetic - large scale changes 50-150%, accelerating stagger).
- **emotion_mapping**: `emotion-mapping.md:9` (Urgency/Alert - Sharp, fast, direct / 100-200ms).
