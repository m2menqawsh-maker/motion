# دليل اقتراح القوالب الجديدة (Template Proposal Guide)

## متى تقترح قالباً جديداً؟

اقترح قالباً جديداً عندما:
1. ابتكرت كوداً مخصصاً ممتازاً في `custom/`
2. الكود قابل لإعادة الاستخدام في مشاريع أخرى
3. الكود يحل مشكلة شائعة

## كيف تنشئ اقتراحاً؟

### 1. إنشاء المجلد
```bash
mkdir -p .agents/plugins/super-video-maker-plugin/templates/proposed/<proposal_id>
```

### 2. إنشاء الملفات الأساسية

#### `Component.tsx` (الكود المخصص)
```tsx
import React from 'react';
import { useCurrentFrame, spring } from 'remotion';

export const MyCustomTemplate: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const scale = spring({ frame, fps: 30 });
  
  return (
    <div style={{ transform: `scale(${scale})` }}>
      {text}
    </div>
  );
};

export default MyCustomTemplate;
```

#### `proposal.json` (الوصف والخصائص)
```json
{
  "proposal_id": "my-custom-template",
  "name": "My Custom Template",
  "description": "قالب مخصص يعرض النص بحركة نابضة",
  "category": "Typography & Text",
  "author": "AI Agent (tech_world project)",
  "date": "2026-09-02",
  "source_project": "tech_world",
  "source_file": "projects/tech_world/custom/MyCustomTemplate.tsx",
  "props": [
    {
      "name": "text",
      "type": "string",
      "required": true,
      "description": "النص المراد عرضه"
    }
  ],
  "use_cases": [
    "عناوين رئيسية",
    "كلمات مفتاحية"
  ],
  "motion_personality": "Energetic",
  "duration_range": {
    "min_frames": 30,
    "max_frames": 90
  },
  "sfx_recommendations": [
    "pop-soft.wav",
    "whoosh-fast.wav"
  ]
}
```

#### `README.md` (التوثيق)
```markdown
# My Custom Template

## Overview
قالب مخصص يعرض النص بحركة نابضة.

## Usage
```tsx
import MyCustomTemplate from '@templates/my-custom-template';

<MyCustomTemplate text="Hello World" />
```

## Props
- `text` (string, required): النص المراد عرضه

## Examples
### مثال 1: عنوان رئيسي
```tsx
<MyCustomTemplate text="مرحباً بالعالم" />
```

### مثال 2: كلمة مفتاحية
```tsx
<MyCustomTemplate text="بايثون" />
```
```

### 3. فحص الجودة
```bash
python .agents/plugins/super-video-maker-plugin/scripts/template_proposal_validator.py my-custom-template
```

### 4. الترقية (بعد الموافقة)
```bash
python .agents/plugins/super-video-maker-plugin/scripts/promote_template.py my-custom-template
```

## أمثلة على قوالب مقترحة ناجحة

### مثال 1: Dynamic Camera with Paths
- **المشروع الأصلي:** `tech_world`
- **الوصف:** كاميرا تتنقل بين كلمات متناثرة مع رسم مسارات نيون
- **التصنيف:** Cinematic Engine Primitives

### مثال 2: Interactive Cards
- **المشروع الأصلي:** `tech_world`
- **الوصف:** بطاقات زجاجية تتفاعل مع بعضها عند الظهور
- **التصنيف:** UI & Layouts

## الفحص التلقائي

عند تشغيل `template_proposal_validator.py`، سيتم فحص:
- ✅ وجود الملفات الأساسية
- ✅ صحة proposal.json
- ✅ التوافق مع TypeScript
- ✅ عدم وجود أنماط خطيرة
- ✅ وجود التوثيق الكامل
- ✅ التوافق مع بقية القوالب

إذا نجح الفحص، يمكن ترقية القالب إلى `templates/` وتحديث `TEMPLATE_INDEX.md` تلقائياً.
