# 🗂️ TEMPLATE_REGISTRY

هذا المجلد يحتوي على السجل الموحد لجميع قوالب `snapcn` و `remocn` المتوفرة في النظام والمقروءة آلياً بواسطة الواجهة الرسومية (GUI).

## الهيكلية:
- `types.ts`: واجهات السجل وتوصيف الـ schema الخاص بكل قالب.
- `template-registry.tsx`: السجل المصدري الذي يُسجل كل القوالب بشكل صريح مع المكون الفعلي والصور المصغرة.
- `docs-extractor.ts`: أداة لتوليد `auto-generated-entries.ts` مؤقتاً من التوثيق (markdown) لتسهيل التسجيل اليدوي لاحقاً.
- `thumbs/`: مجلد يحتوي على الصور المصغرة لكل قالب، والتي يتم توليدها بواسطة السكربت `scripts/gen_thumbs.ts`.

## كيفية إضافة قالب جديد:
1. قم بتشغيل مستخرج التوثيق أولاً لجلب الخصائص:
   ```bash
   npx tsx registry/docs-extractor.ts
   ```
2. انسخ القالب الجديد من `registry/auto-generated-entries.ts`.
3. أضفه يدوياً إلى `registry/template-registry.tsx` مع تعبئة:
   - `label` (عربي/إنجليزي)
   - `category`
   - `defaults` (بحيث يطابق الـ `StyleSurface`)
4. قم بتشغيل الاختبارات للتأكد من سلامة التسجيل:
   ```bash
   npx vitest run tests/registry.test.ts
   ```
5. قم بتوليد الصورة المصغرة عبر سكربت الرندر:
   ```bash
   npx tsx scripts/gen_thumbs.ts
   ```
