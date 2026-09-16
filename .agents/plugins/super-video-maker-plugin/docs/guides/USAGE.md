# دليل الاستخدام

## القاعدة الوحيدة
لإنشاء فيديو، استخدم فقط:
```bash
python scripts/pipeline.py <project_id>
```

## الأوامر المحظورة
- ❌ `npm run studio`
- ❌ `npx remotion render`
- ❌ أي أمر يبني الفيديو يدوياً

## سير العمل
1. أنشئ مشروعاً: `python scripts/scaffold_project.py <project_id>`
2. اكتب الخطة والمخطط.
3. شغل المنسق: `python scripts/pipeline.py <project_id>`
4. المنسق سيتولى كل شيء: البوابات، الفحوصات، الرندر.
