---
name: snapcn
description: Build Remotion videos with snapcn. You only select components from the template registry and plan the blueprint. Do not build videos manually.
---

# snapcn

## القاعدة المطلقة
أنت لا تنشئ مكونات جديدة. أنت لا تستخدم `shadcn`. أنت لا تستخدم `npx create-video`.
كل المكونات موجودة مسبقاً في `templates/elements/` و `templates/scenes/`.

## مهمتك الوحيدة
1. اختر القوالب المناسبة من `templates/elements/` و `templates/scenes/`.
2. اجمعها في ملف `05_blueprint.json` وفقاً لـ `contracts/blueprint.ts`.
3. اترك `scripts/pipeline.py` يقوم بالرندر.

## القوالب المتاحة
[قائمة بالقوالب الموجودة في `registry/template-registry.tsx`]

## الأوامر المحظورة
- ❌ `npx remotion`
- ❌ `npm run studio`
- ❌ `shadcn add`
- ❌ `npx create-video`
- ❌ أي أمر يبني الفيديو يدوياً
