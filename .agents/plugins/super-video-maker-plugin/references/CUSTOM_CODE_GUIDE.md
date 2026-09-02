# دليل منطقة الابتكار المحكومة (Custom Code Guide)

## متى تستخدم الكود المخصص؟

استخدم الكود المخصص **فقط** عندما:
1. لا يوجد قالب في `TEMPLATE_INDEX.md` يلبي احتياجك
2. تحتاج تفاعلاً معقداً جداً لا توفره القوالب
3. المستخدم طلب شيئاً فريداً تماماً

## كيف تكتب كوداً مخصصاً؟

### 1. أنشئ الملف في المكان الصحيح
```
projects/<project_id>/custom/Scene3_CustomAnimation.tsx
```

### 2. استخدم التوثيق الإلزامي
```tsx
/* CUSTOM CODE
 * Purpose: حركة كاميرا ديناميكية مع رسم مسارات بين الكلمات
 * Author: AI Agent (tech_world project)
 * Date: 2026-09-02
 * Templates Used: None (custom implementation)
 * Why Custom: No existing template supports dynamic path drawing with camera sync
 */

import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';

export const CustomAnimation: React.FC = () => {
  // ... الكود الخاص بك
};
```

### 3. تجنب الأنماط الخطيرة
❌ ممنوع:
- `eval()`, `exec()` — تنفيذ كود عشوائي
- `require('child_process')` — أوامر نظام
- `fs.unlink` — حذف ملفات
- `<script>` tags — حقن JavaScript

### 4. اختبر الكود قبل الدمج
```bash
python .agents/plugins/super-video-maker-plugin/scripts/custom_code_validator.py <project_id>
```

## أمثلة على استخدام الكود المخصص

### مثال 1: حركة كاميرا مع رسم مسارات
```tsx
/* CUSTOM CODE
 * Purpose: كاميرا تتنقل بين كلمات متناثرة مع رسم خطوط نيون
 * Author: AI Agent
 * Date: 2026-09-02
 * Why Custom: No template combines camera movement with SVG path tracing
 */

import React, { useMemo } from 'react';
import { useCurrentFrame, spring, interpolate } from 'remotion';

export const DynamicCameraWithPaths: React.FC<{ words: string[] }> = ({ words }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // حساب مواقع الكلمات
  const wordPositions = useMemo(() => {
    return words.map((word, i) => ({
      word,
      x: 100 + (i * 200) % 800,
      y: 100 + Math.floor(i / 4) * 300,
    }));
  }, [words]);

  // حركة الكاميرا
  const cameraX = interpolate(frame, [0, 30], [0, 100], {
    extrapolateRight: 'clamp',
  });

  return (
    <div style={{ transform: `translateX(${-cameraX}px)` }}>
      {wordPositions.map((pos, i) => (
        <div key={i} style={{ position: 'absolute', left: pos.x, top: pos.y }}>
          {pos.word}
        </div>
      ))}
    </div>
  );
};
```

### مثال 2: تفاعل معقد بين العناصر
```tsx
/* CUSTOM CODE
 * Purpose: بطاقات زجاجية تتفاعل مع بعضها عند الظهور
 * Author: AI Agent
 * Date: 2026-09-02
 * Why Custom: Complex interaction logic not available in templates
 */

import React from 'react';
import { useCurrentFrame, spring } from 'remotion';

export const InteractiveCards: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const card1Scale = spring({
    frame: frame - 0,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  const card2Scale = spring({
    frame: frame - 15,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  return (
    <div>
      <div style={{ transform: `scale(${card1Scale})` }}>Card 1</div>
      <div style={{ transform: `scale(${card2Scale})` }}>Card 2</div>
    </div>
  );
};
```

## الفحص التلقائي

عند تشغيل `materialize_project.py`، سيتم فحص الكود المخصص تلقائياً:
```bash
python scripts/custom_code_validator.py <project_id>
```

إذا فشل الفحص، لن يُسمح بالبناء حتى تُصلح الأخطاء.
