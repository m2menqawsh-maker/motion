# Clean Video Workspace API

هذه طبقة API محلية (Local-only) تعتمد على FastAPI وتعمل كمغلف (Wrapper) للسكريبتات الموجودة في المراحل من 0 إلى 5.

## التشغيل

لتشغيل الخادم في بيئة التطوير محلياً:

```bash
npm run api:dev
# أو عبر uvicorn مباشرة
uvicorn api.main:app --reload --port 8787
```

## أمثلة الاستخدام (cURL)

### إنشاء مشروع جديد
```bash
curl -X POST "http://localhost:8787/projects/" \
     -H "Content-Type: application/json" \
     -d '{"name":"مشروع تجريبي","aspect":"9:16","fps":30,"language":"ar"}'
```

### الحصول على حالة مشروع والبوابات
```bash
curl -X GET "http://localhost:8787/gates/<project_id>/status"
```

### بدء مرحلة
```bash
curl -X POST "http://localhost:8787/gates/<project_id>/start/1"
```

### إنهاء مرحلة
```bash
curl -X POST "http://localhost:8787/gates/<project_id>/finish/1"
```

### اعتماد بوابة (Approve Gate)
```bash
curl -X POST "http://localhost:8787/gates/<project_id>/approve/1?by=gui"
```

### قراءة بيانات المشروع الشاملة (project, state, manifest)
```bash
curl -X GET "http://localhost:8787/projects/<project_id>"
```

### رندر المشروع (يبدأ في الخلفية)
```bash
curl -X POST "http://localhost:8787/render/<project_id>"
```

### الاتصال بالـ WebSocket لمراقبة الرندر
يتم عبر مسار:
`ws://localhost:8787/render/<project_id>/ws`
