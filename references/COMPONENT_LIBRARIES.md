> [!NOTE]
> **Source of Truth Hierarchy:**
> This is a Reference Document (Level 5).
> Current Architectural Authority: `ARCHITECTURE_TRUTH.md`
> Agent Instructions Authority: `.agents/AGENTS.md`
> Do not use this document to bypass official pipeline gates or engine boundaries.

# مكتبات المكونات المعتمدة (Component Libraries)

هذا الملف يحتوي على قائمة بالمكتبات المفتوحة المصدر (Open-Source) التي سيتم جلب المكونات منها لتغذية نظام الفيديو (Video Engine). 
لا يتم تثبيت هذه المكتبات كحزم مغلقة (NPM Packages) بالكامل، بل نعتمد على استراتيجية **(Copy-Paste Components)** لضمان امتلاك الكود المصدري وإمكانية تعديله ليتوافق 100% مع بيئة `Remotion`.

---

## 1. مكتبات الفيديو الأصلية (Native Remotion Libraries)
هذه المكتبات متوافقة بنسبة 100% وتعمل مباشرة دون أي تعديلات، لأنها تستخدم إطارات الفيديو (Frames) وحركات `spring()` الأصلية الخاصة بـ Remotion.

| اسم المكتبة | الوصف | حالة التثبيت |
|---|---|---|
| **`@remotion/transitions`** | انتقالات سينمائية جاهزة (Wipe, Fade, Slide). | ✅ مدمجة بالكامل في `templates/effects/` (18 انتقال) |
| **`remotion-bits`** | مكونات جاهزة مثل نصوص متحركة، Particles، ورسوم بيانية. | ✅ مدمجة بالكامل في `templates/elements/` (10 عناصر) |
| **`remotion-ui`** | مكونات واجهة مستخدم مجهزة للعمل مع الفيديو. | ✅ مدمجة وموزعة آلياً في `scenes/` و `elements/` (77 مكوّن) |
| **`snap-cn` (Internal)** | النواة الداخلية لمشروعنا (تشبه Shadcn لريموشن). | مكونات تُبنى برمجياً داخلياً حسب الحاجة |

---

## 2. مكتبات الواجهات التفاعلية (Web UI Micro-interactions)
هذه المكتبات مصممة للويب وتتفوق بصرياً. تتطلب تعديلاً بسيطاً من الذكاء الاصطناعي (AI Adaptation) لاستبدال `Framer Motion` بدوال `Remotion` لتعمل بتوافق تام.

| اسم المكتبة | الرابط | أبرز المكونات |
|---|---|---|
| **Aceternity UI** | [ui.aceternity.com](https://ui.aceternity.com) | بطاقات 3D، نصوص الآلة الكاتبة، خلفيات مضيئة (Aurora)، ومؤثرات توهج. |
| **Magic UI** | [magicui.design](https://magicui.design) | Bento Grids، نصوص لامعة (Shiny Text)، أشرطة تمرير (Marquee)، أزرار براقة. |
| **Motion Primitives** | [motion-primitives.com](https://motion-primitives.com) | بطاقات تتوسع (Expandable Cards)، تبويبات حركية (Animated Tabs)، وانتقال نصوص متبلورة. |
| **React Bits** | [reactbits.dev](https://reactbits.dev) | نصوص مشفرة (Decrypted Text)، خلفيات متحركة، وتمويه النصوص (Blur Text). |
| **Animate UI** | [animate-ui.com](https://animate-ui.com) | نصوص تلميحية عائمة (Fluid Tooltips)، نوافذ منبثقة (Popups). |

---

## 🛠️ آلية إدراج أي قالب (Workflow)
عند الحاجة لإضافة مكون من الجدول أعلاه:
1. **اختيار المكون**: انسخ كود الـ React من الموقع المستهدف.
2. **التنظيف والتهيئة**: اطلب من الوكيل (AI) تحويل الكود ليدعم إطارات الفيديو `useCurrentFrame` وإزالة `Framer Motion`.
3. **التسجيل (Registry)**: يقوم الوكيل بعمل مكوّن وسيط (Wrapper) لربطه بخصائص النظام (`surface` و `content`).
4. **التصنيف**: يتم وضع المكون في المجلد الصحيح:
   - `templates/elements/` (للعناصر الصغيرة كالأزرار والنصوص)
   - `templates/scenes/` (للبطاقات الكبيرة والمشاهد)
   - `templates/effects/` (للانتقالات والخلفيات)
