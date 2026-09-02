# مصفوفة ربط SFX بالإيماءات البصرية (إلزامية)

## 📌 القواعد الصارمة:
1. كل إيماءة بصرية (من §3 Emphasis Grammar في `user-signature-style.md`) **يجب** أن يكون لها SFX مطابق من هذه المصفوفة.
2. لا يُسمح بإيماءة بصرية صامتة.
3. لا يُسمح بتكرار نفس ملف SFX في مشهدين متتاليين.
4. يجب قراءة هذه المصفوفة قبل كتابة أي خطة مشهد.

## 🎼 الجدول الإلزامي:

| الإيماءة البصرية | SFX الأساسي | SFX البديل (إذا تكرر) | التوقيت | مستوى الصوت |
|---|---|---|---|---|
| **Neon Ring** (دائرة نيون للأرقام/الوعود) | `chime-soft.wav` | `bell-subtle.wav`, `crystal-ring.wav` | 0ms (بداية الظهور) | -24 LUFS |
| **Marker Underline** (خط ماركر للخلاصات) | `swish-metal.wav` | `whoosh-soft.wav`, `brush-stroke.wav` | 0ms | -24 LUFS |
| **Highlighter BG** (خلفية مظللة للقواعد) | `soft-whoosh.wav` | `brush-sweep.wav`, `air-whoosh.wav` | -50ms (قبل ظهور النص) | -28 LUFS |
| **Strikethrough** (خط شطب أحمر للنفي) | `glitch-cut.wav` | `digital-error.wav`, `static-burst.wav` | 0ms | -24 LUFS |
| **Flash Cut** (ومضة للتأكيد) | `dramatic-boom.wav` | `cinematic-impact.wav`, `thunder-clap.wav` | 0ms | -20 LUFS |
| **Typewriter** (كتابة كود/نصوص) | `mechanical-keyboard.wav` | `typewriter-ding.wav`, `key-click.wav` | كل 80ms (كل حرف) | -28 LUFS |
| **Zoom Through** (زوم عميق للانتقال) | `whoosh-deep.wav` | `cinematic-swoosh.wav`, `wind-rush.wav` | -100ms (قبل الزوم) | -24 LUFS |
| **Shock Zoom** (زوم صدمة للتأكيد) | `vine-boom.wav` | `impact-hard.wav`, `bass-drop.wav` | 0ms | -18 LUFS |
| **Card Pop** (ظهور بطاقة/إشعار) | `pop-soft.wav` | `click-subtle.wav`, `notification-ding.wav` | 0ms | -24 LUFS |
| **Slide Reveal** (سحب/كشف) | `swish-fast.wav` | `whip-pan.wav`, `slide-whoosh.wav` | 0ms | -24 LUFS |
| **Transition** (انتقال بين المشاهد) | `transition-whoosh.wav` | `page-turn.wav`, `glass-shatter.wav` | -100ms (قبل الانتقال) | -24 LUFS |
| **Stat Counter** (عدّاد رقمي) | `tick-soft.wav` | `stat-click.wav`, `counter-beep.wav` | كل 200ms (كل رقم) | -28 LUFS |
| **Chart Animation** (رسم بياني) | `data-flow.wav` | `chart-draw.wav`, `graph-rise.wav` | 0ms | -28 LUFS |
| **Code Block** (ظهور كود) | `terminal-type.wav` | `code-compile.wav`, `syntax-highlight.wav` | كل 100ms (كل سطر) | -28 LUFS |

## 🚨 الإجراء عند المخالفة:

إذا وجدت خطة مشهد تحتوي على إيماءة بصرية بدون SFX مطابق من الجدول أعلاه:

1. **أضف الـ SFX تلقائياً** من العمود "SFX الأساسي".
2. إذا كان الـ SFX الأساسي مستخدماً في المشهد السابق، استخدم "SFX البديل".
3. سجّل الإضافة في خطة المشهد:
   ```
   ✅ Auto-SFX Injected: [الإيماءة البصرية] → [اسم ملف SFX]
   ```

## 📊 أمثلة على الاستخدام الصحيح:

### مثال 1: مشهد تعليمي (بايثون)
```
الجملة: "بايثون هي اللغة الأسرع تعلماً"

الإيماءات البصرية:
- Neon Ring حول كلمة "بايثون" → SFX: chime-soft.wav
- Marker Underline تحت "الأسرع تعلماً" → SFX: swish-metal.wav
- Code Block يظهر كود بايثون → SFX: terminal-type.wav

النتيجة: 3 إيماءات بصرية → 3 SFX مختلفة ✅
```

### مثال 2: مشهد إحصائيات
```
الجملة: "30 يوم فقط لإتقان البرمجة"

الإيماءات البصرية:
- Neon Ring حول "30 يوم" → SFX: chime-soft.wav
- Stat Counter يعدّ من 1 إلى 30 → SFX: tick-soft.wav (كل 200ms)
- Flash Cut عند "فقط" → SFX: dramatic-boom.wav

النتيجة: 3 إيماءات بصرية → 3 SFX مختلفة ✅
```

### مثال 3: مشهد مقارنة
```
الجملة: "الطريقة القديمة vs الطريقة الجديدة"

الإيماءات البصرية:
- Strikethrough على "الطريقة القديمة" → SFX: glitch-cut.wav
- Card Pop لـ "الطريقة الجديدة" → SFX: pop-soft.wav
- Highlighter BG تحت الخلاصة → SFX: soft-whoosh.wav

النتيجة: 3 إيماءات بصرية → 3 SFX مختلفة ✅
```

## 🛑 قاعدة التوقف الصارمة:

إذا وجدت خطة مشهد بدون SFX مطابق لكل إيماءة بصرية:
- **لا تنتقل** للخطوة ج (جلب الميديا).
- **أضف** الـ SFX المفقودة فوراً.
- **أعد** الفحص حتى ينجح.
