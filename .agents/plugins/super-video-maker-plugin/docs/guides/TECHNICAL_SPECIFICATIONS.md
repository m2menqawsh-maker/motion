# ⚙️ Technical Specifications (v4.0.1)

## 1. الهيكلية المعمارية
- **Pipeline Guard:** الحارس المركزي. يمنع الرندر أو فتح الاستوديو إلا إذا تمت الموافقة، ونُفذت الفحوصات الذكية والنهائية (`require_smart_qc_passed`, `require_final_qc_passed`).
- **Smart QC:** وحدة فحص تتدخل بين بناء المشاهد (Batch Builder) والرندر النهائي. تتأكد من السلامة المرئية.
- **Final QC:** وحدة فحص تعمل مباشرة بعد إخراج الـ MP4 للتأكد من المعايير الفنية (FPS, Codec, Audio Sync).

## 2. متطلبات النظام (Dependencies)
تتولى السكريبتات الجديدة (QC) تثبيت المكتبات اللازمة تلقائياً عبر دالة `ensure_dependencies()`.
- `opencv-python`: لمعالجة الصور واكتشاف الحواف.
- `easyocr` / `paddleocr`: بدائل OCR في حال غياب Tesseract.
- `librosa` & `soundfile`: للتحليل الدقيق للصوت (Clipping, Sync, Noise).
- `ffmpeg-python`: جسر برمجي بين أوامر البايثون وأوامر FFmpeg/FFprobe.

## 3. التكامل مع الـ MCP
- يفضل دائماً استخدام الـ `audio-tools-mcp` للعمليات الصوتية.
- في الفحص النهائي (`final_qc.py`) يتم البحث أولاً عن الـ `ffmpeg` و `ffprobe` بداخل مجلد `.venv/Scripts/` الخاص بـ MCPs المثبتة مسبقاً، وإذا لم يوجد يستخدم `ffmpeg-python`.

## 4. التوازي (Concurrency)
- `batch_builder.py` يستخدم `ThreadPoolExecutor` لبناء ملفات `SceneN.tsx` بسرعة هائلة.
- معدل البناء: يمكن بناء 10 مشاهد في نفس الوقت الذي يستغرقه بناء مشهدين بشكل تسلسلي.
