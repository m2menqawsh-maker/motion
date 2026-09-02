# البنية الجديدة للمشروع (v2.0)

## المبادئ الأساسية

1. **مصدر حقيقة واحد**: كل القوالب في مكان واحد منظم
2. **الراوتر حسب الحاجة**: الاختيار حسب `intent + use_case + mood` وليس حسب المجلد
3. **المحرك السينمائي مكتبة داخلية**: ليس طبقة توجيه مستقلة
4. **المهارات في مكان واحد**: `skills/INDEX.md` هو البوابة الوحيدة

## البنية

```
templates/          # القوالب الموحدة (مصدر الحقيقة)
├── scenes/             # مشاهد كاملة
├── elements/           # عناصر داخل المشهد
└── effects/            # تأثيرات وانتقالات

engine/                 # المحرك السينمائي (أدوات داخلية)
├── camera/
├── cursor/
├── layout/
├── audio/
└── choreography/

vendor/                 # مكتبات خارجية خام
├── onda/
├── remotion-ui/
├── remocn/
├── snapcn/
└── remotion-bits/

ground-truth/           # الفهارس المولدة آلياً
├── collections/        # مجموعات استخدام
└── CANONICAL_PATHS.json

skills/                 # المهارات (مكان واحد)
├── INDEX.md
├── super-video-maker/
├── remocn/
└── snapcn/
```

## دورة حياة القالب

```
1. vendor/onda/BlurReveal.tsx (خام)
   ↓ (اختبار + تطبيع RTL + Probe QC)
2. templates/elements/typography/BlurReveal.tsx (معتمد)
   ↓ (يظهر في TEMPLATE_INDEX.md)
3. يصبح متاحاً للراوتر
```

## الراوتر الجديد

الاختيار يكون حسب:
```
intent + use_case + mood + type + quality
```

وليس حسب:
```
المجلد أو الطبقة أو المصدر
```

## المراحل

- [x] المرحلة 1: إنشاء البنية الجديدة
- [x] المرحلة 2: نقل القوالب المعتمدة
- [x] المرحلة 3: تحديث الكتالوج والفهارس والسكريبتات (مع التصحيحات الشاملة)
- [x] المرحلة 4: تفعيل الراوتر الموحد
- [ ] المرحلة 5: اختبار على مشروع جديد

## إنجازات المرحلة 4

- [x] تصحيح مشكلة schema.ts في الفهرسة
- [x] تصحيح تتبع مصدر remocn
- [x] ملء بيانات التصنيف (use_cases, intents, moods, capabilities)
- [x] توليد ملفات collections/ آلياً
- [x] إنشاء template_router.py
- [x] اختبار الراوتر على 5 حالات
- [x] تحديث ROUTER.md §6 بتعليمات الراوتر
- [x] تحديث skills/INDEX.md

## ملاحظات المرحلة 4

- الراوتر يعمل بنظام النقاط: كل معيار مطابقة يضيف نقاطاً، والنتائج تُرتب تنازلياً.
- ملفات `collections/` تُحدّث آلياً عند تشغيل `build_ground_truth.py`.
- `template_router.py` أداة مساعدة للوكيل، لكنها لا تحل محل قراءة الكتالوج مباشرة عند الحاجة.
- [x] تصحيح validate_blueprint.py للسماح بالانتقالات
- [x] تصحيح MCP_INDEX (كان 0 بسبب خطأ في المنطق)
- [x] تحديث VOCAB_REMAP.md بالمسارات الجديدة
- [x] التحقق من CINEMATIC_INDEX.md
- [x] تصحيح حقل source في الكتالوج
- [x] تحديث ROUTER.md بالكامل
- [x] تحديث video-production-protocol.md
- [x] تحديث AGENTS.md
