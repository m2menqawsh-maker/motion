# 📦 Project Templates Guide

## 1. الفكرة
القوالب الجاهزة توفر الوقت وتسمح بتوليد مشاريع بسرعة بضغطة زر دون الحاجة للبدء من الصفر. جميع القوالب موجودة في مسار `.agents/project_templates/`.

## 2. القوالب المتاحة
- **tech_promo_30s:** فيديو ترويجي لتقنية أو أداة، سريع الحركة (30 ثانية).
- **educational_60s:** فيديو تعليمي طويل نسبياً (60 ثانية) مع مساحات أوسع للنصوص والشروحات.
- **product_showcase:** عرض منتج ديناميكي (15 ثانية) يعتمد على عرض الصور والألوان البارزة.

## 3. كيفية الاستخدام
لإنشاء مشروع جديد من قالب، استخدم أداة سطر الأوامر التالية من المسار الأساسي:

```bash
python .agents/project_templates/create_from_template.py <template_name> <project_id>
```

مثال:
```bash
python .agents/project_templates/create_from_template.py tech_promo_30s my_new_app_video
```

## 4. إنشاء قوالب جديدة
يمكنك إضافة أي قالب جديد عبر إنشاء مجلد جديد بداخل `.agents/project_templates/` ووضع ملف `config.json` داخله بالإضافة للملفات الأساسية للمشروع.
