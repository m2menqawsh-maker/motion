# Layer Stack — القاعدة الخماسية الإلزامية لكل مشهد
> المصدر: remotion-cinematic + LottieFiles. تُطبق على كل مشهد Remotion بدون استثناء.

## الطبقات الخمس (من الأسفل للأعلى)
1. **Background** — لقطة حقيقية أو gradient، معتّمة ومشوّشة دائماً: `filter: brightness(0.8) blur(4px)`
2. **Atmosphere** — أجواء ضوئية: `film-burn` (opacity ≤ 0.4) أو `bokeh-circles` أو `gradient-shift`
3. **Mid-ground** — الأدلة والبطاقات: حاويات بعرض ظل وperspective من عائلة Containers & Cards
4. **Foreground** — focal point واحد فقط: عنوان/نص بظل `textShadow: 0 4px 20px rgba(0,0,0,0.5)`
5. **Overlay** — لمسة سينمائية: `noise-grain` (noiseAmount 0.05) + `vignette-pulse`

## Depth Checklist (إلزامي قبل أي رندر)
- [ ] كل مشهد فيه 3 طبقات حركة على الأقل (primary + secondary + ambient)
- [ ] focal point واحد فقط (hero element واحد)
- [ ] كل نص له ظل؛ كل بطاقة لها ظل/perspective
- [ ] الخلفية تتحرك ببطء (parallax / ken-burns) — ممنوع خلفية ثابتة
- [ ] ممنوع linear للحركة المكانية؛ ممنوع opacity-only لعنصر مهم
- [ ] أي حركة أكبر من 1/3 الشاشة تحتاج keyframe وسيط

## Safe Zones (من PROJECT_MASTER_MANUAL)
- PiP بلا إطار: أعلى-يمين `x=1378, y=50`، زوايا 24px، ظل ناعم — ممنوع الإطار الصلب
- كابشن كاريوكي: الشريط السفلي ~20% من الارتفاع، Arial Black، 2-3 كلمات، الكلمة الحالية أصفر/برتقالي + ظل داكن
- ممنوع وضع نص مهم داخل المنطقتين أعلاه
