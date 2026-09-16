# VOCAB_REMAP — جدول الأسماء الوهمية → الحقيقية
> قاعدة إلزامية: ممنوع على الـ Agent استيراد أي اسم غير موجود في TEMPLATE_INDEX.md.
> إذا لم يوجد الاسم في الفهرس → ابحث هنا → إن لم يوجد → توقف واسأل المستخدم.

| الاسم الوهمي (محفوظ بالذاكرة) | موجود؟ | البديل الحقيقي (من templates-new/) |
|---|---|---|
| typewriter-subtitle | ❌ | Captions أو WordStagger (من premium-templates) |
| glitch-text | ❌ | RgbGlitchText (من premium-templates) |
| ken-burns | ❌ | templates-new/scenes/ken-burns/KenBurns.tsx |
| stat-counter | ❌ | StatCard (من premium-templates) |
| terminal-window | ❌ | Terminal (من premium-templates) |
| code-block | ❌ | CodeBlock (من premium-templates) |
| whip-pan | ❌ | whip-pan (من premium-templates) |
| split-screen | ❌ | SplitScreen (من premium-templates) |
| 3d-card-flip | ❌ | CardStack / Carousel (من premium-templates) |
| kinetic-typography | ❌ | WordStagger / BlurReveal / TrackingIn (من premium-templates) |
| film-grain | ❌ | noise-grain |
| light-leak | ❌ | film-burn |
| gradient-mesh | ❌ | gradient-shift |

## البروتوكول
1. قبل كتابة أي import: افتح TEMPLATE_INDEX.md.
2. الاسم غير موجود؟ ابحث في هذا الجدول واستخدم البديل الحقيقي.
3. غير موجود هنا؟ يُسمح بتركيب قوالب موجودة (layering)؛ يُمنع كتابة قالب جديد من الصفر — توقف واسأل.
