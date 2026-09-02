# ROUTER.md — محرك القرار: متى MCP / متى أداة / متى قالب / متى مرجع
> هذا الملف هو العقل الموجّه. أي مهمة فيديو تمر هنا أولاً قبل أي كود.

## §1 الـ Pipeline العالمي (مستوحى من patterns/index.ts)
Validation (هل الطلب مهمة فيديو؟) → Recipe Match → Skill Detection → Suitability Gate → Build → Verify → QC
1. Validation: إن لم يكن الطلب مهمة فيديو/موشن → لا تُفعّل المهارة.
2. Recipe Match: `python tools/video_recipes.py match --goal "<الهدف>"` إلزامي قبل أي بناء.
3. Skill Detection: حدد المراجع المطلوبة من §7 واقرأها قبل الكود.
4. Suitability Gate: قبل قبول أي أصل: هل اللون يناسب الـ palette؟ هل النبرة تناسب الـ mood؟ هل الأسلوب يطابق باقي العناصر؟ إن لا → استبدله.
5. Build: قوالب من TEMPLATE_INDEX فقط + layer-stack + personality.
6. Verify: scripts/verify/ (seek-shot.sh → contact-sheet.sh → probe-mp4.sh).
7. QC: ffmpeg_qc.py + broll_layout_qc.py + ad_quality_gate.py حسب نوع الفيديو.

## §2 جدول الـ MCPs السبعة (التفاصيل الكاملة: ground-truth/MCP_INDEX.md)
| الخادم | متى يُستخدم (إلزامي) | أبرز الأدوات |
|---|---|---|
| audio-tools-mcp | أول خطوة تقنية عند وجود صوت/VO | analyze_voiceover → timings، detect_and_trim_silence، trim_audio، extend_audio، normalize_loudness (-16 LUFS)، split_voiceover_sentences، build_voiceover_timeline |
| media-sources-mcp | أي أصل حي: stock/أيقونة/SFX/رابط مباشر | pixabay_search_*، pexels_search_*، freesound_search، iconify_search، download_iconify_icon، download_direct_file، change_asset_status |
| video-tools-mcp | قص/تمديد/أبعاد/إطارات سوداء للفيديو | trim_video، extend_video، resize_video، detect_and_trim_black_frames |
| image-tools-mcp | ترقية صور/قص نسب/حذف هوامش | upscale_image، crop_to_ratio، auto_crop_content |
| common-tools-mcp | قبل أي معالجة (check_cache) وبعدها (save_to_cache) | check_cache، save_to_cache |
| ffmpeg-mcp-server | مهام FFmpeg طويلة بالخلفية + حالة/إلغاء/دمج | jobs API |
| Video_Editor_MCP | أوامر FFmpeg حرة فقط إن لم تغطِّها أداة متخصصة | freeform + progress |

### مصفوفة القرار السريع (أي خادم؟ أي أداة أولى؟)
| المهمة | الخادم الإلزامي | الأداة الأولى |
|---|---|---|
| تحليل VO ومواقع الكلمات | audio-tools-mcp | analyze_voiceover |
| جهارة -16 LUFS | audio-tools-mcp | normalize_loudness |
| بحث B-Roll/صور/أيقونات | media-sources-mcp | pexels_search_videos / iconify_search |
| تنزيل SVG ملون | media-sources-mcp | download_iconify_icon |
| قص نسب/ترقية صور | image-tools-mcp | crop_to_ratio / upscale_image |
| أبعاد فيديو/إطارات سوداء | video-tools-mcp | resize_video / detect_and_trim_black_frames |
| فحص معالج مسبقاً | common-tools-mcp | check_cache |
| رندر خلفية/دمج | ffmpeg | concatenate_videos / check_processing_status |
| أمر FFmpeg حر | video-editor | execute_command |
> أمثلة JSON الكاملة: `reference/mcp-toolbook.md` • أولوية المصادر: مرفوع المستخدم → كاش → بوابة (ROUTER §10)

## §3 جدول أدوات Python الـ19 (التفاصيل: ground-truth/TOOLS_INDEX.md)
video_recipes.py (match/plan/validate أولاً) • video_orchestrator.py (دورة حياة الوظيفة) • elevenlabs_voice.py • heygen_client.py • fal_seedance_video.py • image_provider.py • replicate_video.py (احتياطي) • screen_recorder.py + agent_browser_recorder.py • demo_video_composer.py • video_captioner.py • music_provider.py • local_explainer_broll.py • ugc_ad_runner.py • media_pipeline.py (تنسيق دورة حياة الأصول) • ffmpeg_qc.py • broll_layout_qc.py • ad_quality_gate.py + materialize_project.py (بوابة نقل الميديا للبناء — scripts/)

## §4 راوتر نوع الفيديو (الـ17 وصفة كاملة)
| الهدف | الوصفة | المرجع |
|---|---|---|
| شرح SaaS / إطلاق منتج مستمر | living-canvas-explainer | LIVING_CANVAS_PLAYBOOK + cinematic/ENGINE.md |
| مفهوم متعدد المستويات هرمي | tabletop-levels-explainer | TABLETOP_EXPLAINER_PLAYBOOK |
| وثائقي فكري / فكرة واحدة | motion-collage-explainer | MOTION_COLLAGE_STYLE |
| إعلان تحويل بدون متحدث | faceless-broll-ad | ad-spine/ad-creative + platform-specs |
| إعلان UGC صانع محتوى خيالي | ugc-ai-ad | HYPERREALISTIC_IMAGE_SOP |
| مراجعات منافس واقتناص عملاء | review-conquest-compilation | REVIEW_VIDEO_PLAYBOOK |
| إثبات متصفح وتصفح آلي | agent-browser-proof | agent_browser_recorder.py |
| شورت مقال + رأس عائم سريع | misotts-article-sprint | HOOK_PLAYBOOK_ARTICLE_SPRINT |
| شورت إنستغرام مقسوم شاشة | avatar-insta-split | commands/avatar-insta-reel.md |
| هوك أفاتار سيلفي + B-roll | avatar-hook-broll | SEEDANCE_AVATAR_ROI + commands/avatar-vo-reel.md |
| استعراض منتج مع مؤسس/أفاتار | avatar-product-walkthrough | WORKFLOW_EXAMPLES #1 |
| أفاتار إخباري متكامل + إثباتات | avatar-explainer | WORKFLOW_EXAMPLES #10 + SEEDANCE_AVATAR_ROI |
| أفاتار VO فوق B-Roll بالكامل | avatar-vo-broll | commands/avatar-vo-reel.md |
| متحدث موجود + كابشن كاريوكي | captioned-talking-head | remotion/captions + WORKFLOW_EXAMPLES #3 |
| استعراض شاشة تفاعلي SaaS | screencast-demo | demo_video_composer.py |
| موشن جرافيك برمجياً Remotion/HTML | motion-graphics | WORKFLOW_EXAMPLES #4 + REMOTION_VIDEO_GUIDE |
| تقطيع طويل لـ Shorts اجتماعية | longform-repurpose | SPOKEN_VO_HUMANIZER + WORKFLOW_EXAMPLES #5 |

## §5 راوتر الذوق (Mood → Personality)
> **تحذير: لا تربط مجال المنتج بشخصية الحركة.** منتج طبي يمكن أن يكون Cinematic أو Energetic. يجب أخذ مجال المنتج للصياغة، وأخذ الـ Personality للحركة حصراً.

| المزاج | الشخصية | الأرقام |
|---|---|---|
| طبي/فاخر/جاد | Cinematic | 350-600ms، cubic-bezier(0.4,0,0.2,1)، overshoot 0% |
| شبابي/ترويجي سريع | Energetic | 100-250ms، ease-out-expo، 15-30% |
| أطفال/مرح | Playful | 150-300ms، ease-out-back، 10-20% |
| تقني/SaaS دقيق | Technical | 200-400ms، cubic-bezier(0.2,0,0,1)، 0-3% |
اقرأ قبل البناء: motion-taste/director/motion-personality.md + emotion-mapping.md

## §6 راوتر القوالب الموحد (Recipe-Driven Template Router)

الترتيب الإلزامي عند اختيار أي قالب:

1. اقرأ الوصفة وحدد:
   - intent (hook, cta, stat, caption, transition, demo, background)
   - type: scene / element / effect
   - use_case (ad, explainer, social, saas, product)
   - mood (cinematic, energetic, technical, playful)
   - capabilities (camera, cursor, ui, terminal, data, captions)
   - min_quality (A, B, C)

2. ابحث في `ground-truth/template_catalog.json` عن كل قالب يطابق المعايير.

3. رتب النتائج:
   - quality A أولاً
   - ثم B
   - ثم C
   - ثم حسب الأدلة البصرية السابقة

4. لا تمنع قالباً من مصدر مختلف إذا كان يحقق الحاجة بجودة أعلى.

5. استخدم مكونات `engine/` فقط عندما يحتاج المشهد قدرات:
   - camera / cursor / windows / layout choreography

6. إذا لم يوجد قالب مناسب:
   توقف واسأل المستخدم.
   ممنوع كتابة قالب من الصفر.

> **ملاحظة**: الفهرس الحي في `ground-truth/TEMPLATE_INDEX.md`.
> الكتالوج الموحد في `ground-truth/template_catalog.json`.
> لا تستخدم `ground-truth/` القديم (مهمل).

### أداة الراوتر الآلي

للبحث عن أفضل قالب، استخدم:
```bash
python scripts/template_router.py --intent <النية> --use-case <حالة_الاستخدام> --mood <المزاج> --type <النوع> --min-quality <الجودة>
```

القيم المتاحة:
- **intent**: hook, cta, stat, caption, transition, demo, background, title_reveal, logo, code_demo, typing, image_motion, camera_movement, overlay, motion_effect, ui_element
- **use-case**: ad, explainer, social, saas, product, education, launch
- **mood**: cinematic, energetic, technical, playful
- **type**: scene, element, effect, engine
- **min-quality**: A, B, C

مثال:
```bash
python scripts/template_router.py --intent hook --use-case ad --mood energetic --type scene --min-quality A
```

> **ملاحظة**: الراوتر يعيد أفضل 5 نتائج مرتبة بالنقاط. اختر الأنسب للمشهد.
> إذا لم تجد نتيجة مناسبة، توقف واسأل المستخدم (§8).

## §7 راوتر المعرفة الخاصة
3D → patterns/3d.md • شات → patterns/messaging.md • رسوم بيانات → patterns/charts.md • إعدادات spring → patterns/spring-physics.md + REMOTION_VIDEO_GUIDE.md • كابشن → remotion/captions/SKILL.md • كاميرا وعمق → cinematic/ENGINE.md + layer-stack.md • أبعاد منصات → patterns/social-media.md + ad-spine/ad-creative/platform-specs.md • كود جاهز → patterns/examples/
فهرس المكونات السينمائية وpropsها → ground-truth/CINEMATIC_INDEX.md

## §8 بروتوكول التوقف والسؤال
لا قالب مطابق؟ → ركّب قوالب موجودة (layering). فشل التركيب؟ → توقف واسأل المستخدم.
إضافة قالب جديد = مراسم مكتبة: نسخ أقرب قالب + تعديل ثوابته فقط + إعادة تشغيل build_ground_truth.py + ثم الاستخدام. ممنوع كود من الصفر إطلاقاً.

## §9 ربط الدفاتر التشغيلية (Playbooks)
| الدفتر | متى يُقرأ |
|---|---|
| VIDEO_COPY_PLAYBOOK.md | قبل كتابة أي نص/سيناريو |
| SPOKEN_VO_HUMANIZER.md | تحويل نص مكتوب إلى VO منطوق |
| HOOK_PLAYBOOK_ARTICLE_SPRINT.md | صياغة الخطاف (أول 3 ثوانٍ) |
| FFMPEG_PLAYBOOK.md | أي عملية FFmpeg يدوية |
| REMOTION_VIDEO_GUIDE.md | الأرقام الرسمية لفيزياء النوابض والتوقيت |
| LIVING_CANVAS_PLAYBOOK.md | وصفة living-canvas-explainer |
| TABLETOP_EXPLAINER_PLAYBOOK.md | وصفة tabletop-levels-explainer |
| MOTION_COLLAGE_STYLE.md | وصفة motion-collage-explainer |
| HYPERREALISTIC_IMAGE_SOP.md | توليد شخصيات UGC واقعية |
| REVIEW_VIDEO_PLAYBOOK.md | وصفة review-conquest-compilation |
| SEEDANCE_AVATAR_ROI.md | قرارات أفاتار Seedance/HeyGen |
| WORKFLOW_EXAMPLES.md | أمثلة تنفيذية كاملة لخطوط الإنتاج |

## §10 Media Pipeline Law — أولوية المستخدم + بوابة واحدة + معالجة نوعية
1. **مرفوع المستخدم مقدّس**: VO/فيديو/صور مرفوعة = المصدر الرسمي؛ يُمنع جلب بديل لها أو توليد VO بـ `elevenlabs_voice.py`.
2. **الكاش يحكم الطرفين**: `check_cache` قبل أي معالجة؛ `save_to_cache` بعدها (common-tools-mcp).
3. **البوابة للناقص فقط**: `media-sources-mcp` حصراً (pixabay/pexels/freesound/iconify/روابط)؛ ممنوع curl/wget/yt-dlp خارجها.
4. **معالجة نوعية**: صوت→audio-tools-mcp (silence→trim/extend→-16 LUFS؛ ولأي VO: analyze_voiceover→split→manifest→timeline أولاً)؛ صورة→image-tools-mcp؛ فيديو→video-tools-mcp؛ مهام خلفية طويلة→ffmpeg؛ أوامر حرة/تصدير→video-editor. ممنوع ffmpeg طرفي يدوي لما يغطيه خادم.
5. **ملاءمة**: المجلوب يمر Suitability Gate (§1)؛ المرفوع يخضع للفحوص التقنية والمساحات الآمنة فقط.
6. **بروتوكول SFX المعالج:** لكل cue: check_cache → trim_audio(مدة المرئي) → afade out 0.2 → normalize_loudness(-24) → save_to_cache → يُسجل processed_path + volume_db + tone في الـ Blueprint.
7. **التنويع الإلزامي:** نفس ملف المؤثر لا يتكرر خلال 8 ثوانٍ؛ انتقالات متتالية تتناوب بين أصلين مختلفين على الأقل؛ إن ضاقت المكتبة → جلب من freesound_search/pixabay_search_audio عبر بوابة الملاءمة (§1) ومعالجتها وتكاشها.
8. **المعالَج الموجود مقدّم على الجلب**: لا يُسجل أي أصل بمصدر mcp_fetch في الـ manifest
   إلا إذا كان ASSET_INDEX.json خالياً من مطابق له. المخالفة = رفض الـ manifest.

## §11 بوابة الموافقة (User Approval Gate)
لا استدعاء لأي نموذج مدفوع/توليدي (HeyGen/Seedance/ElevenLabs/OpenAI/Replicate) قبل اعتماد المستخدم خطة مكتوبة تشمل: الوصفة، العمود الفقري 4 أسطر، قائمة الأصول ومصادرها، التوقيتات، والمنصات المستهدفة.

## §12 التعافي والفشل (Deterministic Repair vs Creative Stop)
- إصلاح حتمي مسموح صامتاً: إعادة محاولة، trim، resize، re-normalize، استبدال أصل مكاش بآخر مكاش.
- أي تغيير إبداعي (زاوية، نص، عائلة قوالب، شخصية حركة) → توقف واسأل (§8).
- فشل بوابة QC ثلاث مرات متتالية → تصعيد للمستخدم مع الأدلة (contact-sheet + probe).

## §13 خط الإنتاج المرحلي المقفول (9 مراحل — إلزامي لكل فيديو)
قاعدة عامة: قبل بدء أي مرحلة شغّل `python scripts/stage_gate.py projects/<id> --check <المرحلة>`؛ exit 1 = توقف فوراً.

### المرحلة 0 — الاستيضاح (🛑 توقف 1)
اطبع الأسئلة الـ18 من ملحق (أ) حرفياً وكاملة وانتظر. ممنوع خطة أو كود قبل الأجوبة. المُخرَج: `00_answers.md`.

### المرحلة 1 — الخطة (🛑 توقف 2)
عمود فقري 4 أسطر + `video_recipes.py match --goal` + personality + جدول أصول (مرفوع/مجلوب) + خطة SFX.
يجب أن تتضمن الخطة حقل `motion_taste_citation` يحتوي اقتباساً من `motion-personality.md:رقم_السطر` أو `decision-framework.md:رقم_السطر` يثبت قراءة قيم الشخصية.
المُخرَج: `01_plan.md` + ملف `01_plan.approved` يُكتب فقط بعد موافقتك الصريحة.

### المرحلة 2 — تجميع الميديا
مرفوعات المستخدم تُبتلع أولاً؛ الناقص: check_cache → media-sources-mcp. كل أصل يُسجل في
`02_asset_manifest.json` بهيكل ملحق (ب-2): id، type، source، path/fetch+fallback، processing chain بخوادم MCP النوعية.
🛑 توقف 4 (Assets Review): قبل الانتقال للمرحلة 3، اعرض للمستخدم مسارات جميع الأصول المجلوبة عبر mcp_fetch.
*للمؤثرات الصوتية SFX تحديداً:* يجب تقديم "وصف نصي" مسموع لما سيسمعه المستخدم (مثال: "صوت نقرة معدني حاد 0.3 ثانية").
انتظر الموافقة الصريحة لإنشاء ملف `02b_assets_reviewed.approved`. ممنوع بدء المرحلة 3 بدونه.

### المرحلة 3 — المعالجة والتطبيع (قانون All-Intra)
- كل فيديو (مرفوعاً أو مجلوباً) يُعاد ترميزه All-Intra قبل دخوله Remotion:
  `ffmpeg -y -i IN -c:v libx264 -x264-params keyint=1:scenecut=0 -crf 16 -preset medium -c:a copy OUT`
  (أو `increase_keyframes`) ثم تحقق بـ `get_files_info` أن GOP=1.
  (السبب الموثق: Long GOP يجعل Chromium يفشل في الـ frame-seeking في Remotion → تقطيع وجمود.)
- فيديو أيضاً: detect_and_trim_black_frames → resize_video. صوت: detect_and_trim_silence → normalize_loudness(-16).
  صورة: auto_crop_content → upscale_image → crop_to_ratio.
- مشاهد متتالية من نفس المصدر: تحقق Seamless Cut (آخر فريم ↔ أول فريم).
المُخرَج: `03_preprocess_report.json` — stage_gate يرفض إن لم يكن لكل فيديو `keyframe_mode:"all_intra"` و`gop:1`.

### المرحلة 4 — التوقيتات
`analyze_voiceover` → `04_timings.json` (حتى لو VO مرفوعاً).

### المرحلة 5 — Blueprint (🛑 توقف 3)
JSON ثانية-بثانية بهيكل ملحق (ب) الكامل (عناصر بكل الحقول، taken_from، locks، طبقات، coverage، sfx) +
`validate_blueprint.py --md` → PASS → تقرأ النسخة البشرية → `05_blueprint.approved` بعد موافقتك.
كل cue في sfx يحمل إلزامياً: asset, at_ms, tone, volume_db, processing (§10.6) وإلا رفض validate_blueprint.
ملف حالة القفل: `.blueprint_lock.json` (يُنشأ تلقائياً عند قفل الـ Blueprint عبر `validate_blueprint.py --lock` لمنع خرق القوالب).

### المرحلة 6 — البناء
شغّل `python scripts/materialize_project.py projects/<id>` أولاً (ينقل الميديا والقوالب من المصادر المعتمدة ويكتب media_map.json)؛ ممنوع نسخ ميديا يدوياً؛ ثم كود من الـ Blueprint فقط + `template_lint.py --verify-build`.

### المرحلة 7 — رندر ومعاينة متدرجة
رندر ثوانٍ قليلة → معاينة → contact-sheet → إصلاح. ممنوع رندر كامل قبل معاينة جزئية ناجحة.

### المرحلة 8 — QC والتسليم
ffmpeg_qc + broll_layout_qc + ad_quality_gate + probe-mp4 → `08_qc_report.json`.

### ملحق (أ) — أسئلة الاستيضاح الـ19 (تُطبع كاملة حرفياً)
1. الهدف الواحد؟ (تحويل/بيع، توعية، تعليم، إطلاق)
2. المشاهد الواحد بدقة؟ (شخصية واحدة)
3. المنصة والنسبة؟ (9:16 / 16:9 / 1:1 / متعدد)
4. المدة بالثواني؟ (أو سقف أقصى)
5. الخطوة التالية في النهاية (CTA)؟
6. مجال العمل (Product Domain): ما هو مجال المنتج/الخدمة؟ (لغة النص فقط).
7. المزاج المطلوب (Motion Personality): اختر مزاجاً واحداً (Cinematic, Energetic, Playful, Technical) للحركة.
8. هوية ثابتة؟ (شعار/ألوان/خطوط) أرفقها
9. ممنوعات بصرية؟
10. ماذا سترفع أنت؟ (VO/فيديوهات/صور/شعار) عدّد
11. ما الناقص الذي أجلبه من MCP؟
12. لقطات حقيقية أم ستوك يكفي؟
13. الفويس: تسجيلك / ElevenLabs / بدون؟
14. إن توليد: اللغة وطابع الصوت؟
15. الموسيقى: هادئة/حماسية/بدون؟ + هل تريد SFX؟
16. أفاتار متحدث أم faceless؟
17. كابشن كاريوكي دائم أم نقاط مفتاحية؟
18. عناصر إجبارية الظهور؟ (سعر/عداد/مقارنة/أيقونة)
19. تأكيد: لا استدعاء مدفوع قبل موافقتك على الـ Blueprint؟ (افتراضي: نعم)

### ملحق (ب) — الهيكل الإلزامي لعنصر Blueprint (ب-1) وأصل (ب-2)
(ب-1) عنصر:
{"id","kind":"template|video|image|icon|text|caption|sfx|music","template","asset_ref",
 "props":{...},"start_sec","end_sec","frames":[a,b],
 "lock":{"type":"word","word_index":N} أو {"type":"absolute_ms","ms":X},
 "layout":{"zone","x_pct","y_pct","coverage_pct","layer":1-5},
 "motion":{"enter","exit","easing","duration_ms"},
 "taken_from":"templates/x.tsx | ${PLUGIN_DATA}/assets/sfx/... | engine/... | mcp:server/tool",
 "paid":false,"notes"}
(ب-2) أصل:
{"asset_id","type","source":"user_upload|cache|mcp_fetch|generated","path",
 "fetch":{"server","tool","query"},"fallback":{"tool","query"},
 "processing":["...","all_intra"],"covers_sec":[a,b]}
