---
name: snapcn
description: Build Remotion videos with snapcn. Select components from the template registry and plan the blueprint, or enter custom creation mode to build custom React/TSX templates (Level 1/0) if no matching template exists.
---

# snapcn

## 1. القاعدة الأساسية (المسار المعياري - Level 2)
الأولوية القصوى دائماً هي استخدام القوالب الجاهزة من السجل:
1. ابحث عن القوالب المناسبة في `templates/elements/` و `templates/scenes/` (استخدم `scripts/validators/inspect_template.py <TemplateName>`).
2. اجمعها في ملف `05_blueprint.json` وفقاً لـ `contracts/blueprint.ts`.
3. دع `scripts/pipeline.py` يتولى التجميع والتحقق والرندر.

---

## 2. وضع إنشاء الكود المخصص (Custom Creation Mode - Level 1 / Level 0)
**متى يُفعّل هذا الوضع؟**
إذا بحثت في سجل القوالب الجاهزة **ولم تجد قالباً مناسباً** يفي بمتطلبات المشهد أو الرؤية الفنية، يتم تفعيل وضع إنشاء كود React/TSX مخصص داخل "منطقة الابتكار المحكومة" وفق مستويين:
- **Level 0 (Primitive Block):** إنشاء مكوّن ذري جديد (Lego Block) بصيغة `.tsx`.
- **Level 1 (Composite Scene):** دمج مكوّنات Level 0 مع عناصر من `templates/elements` في مشهد متكامل.

### ضوابط وقواعد كتابة كود React المخصص:
1. **مسار الحفظ:**
   - احفظ الملف داخل `templates/custom/<ComponentName>.tsx` أو `projects/<project_id>/custom/<ComponentName>.tsx`.
2. **هيكل المكون الإلزامي:**
   - يجب أن يقبل المكون الخصائص القياسية الثلاث:
     ```tsx
     export const ComponentName = ({ surface, content, template_props }: any) => { ... }
     ```
   - يجب تصدير مخطط Zod للتحقق من المدخلات:
     ```tsx
     export const schema = z.object({ ... });
     ```
3. **التوثيق الإلزامي (DocBlock):**
   - يجب أن يبدأ الملف بتعليق توثيقي بالشكل التالي (يفحصه `custom_code_validator.py`):
     ```tsx
     /* CUSTOM CODE
      * Purpose: <الغرض الدقيق من المكون>
      * Author: Agent
      * Date: <التاريخ الحالي>
      */
     ```
4. **الفحص والتحقق الإلزامي:**
   - شغّل فحص التحقق من القالب:
     `python scripts/validators/validate_template.py <path_to_tsx>`
   - تأكد من اجتياز فحص `python scripts/validators/custom_code_validator.py`.
   - تأكد من عدم وجود أخطاء TypeScript (`npx tsc --noEmit`).

---

## 3. الأوامر المحظورة قطعياً
- ❌ **حظر تام:** كتابة سكربتات بايثون لتوليد أو دمج كود React آلياً (مثل `generate_react.py`). يجب كتابة ملف الـ `.tsx` مباشرة.
- ❌ `npx remotion` أو `npm run studio` أو `npm run build` بشكل يدوي مباشر (التشغيل حصراً عبر سكربتات المنظومة: `scripts/open_studio.py` و `scripts/render_project.py`).
- ❌ `shadcn add` أو `npx create-video`.
- ❌ استخدام أوامر نظام خطيرة في كود React (`eval`, `exec`, `child_process`, `fs.unlink`, `process.exit`).
- ❌ تخطي البوابات أو فك القفل دون موافقة المستخدم الصريحة.
