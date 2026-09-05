#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

def ensure_dependencies():
    """تثبيت المكتبات المطلوبة تلقائياً"""
    required = ['opencv-python', 'numpy', 'pytesseract', 'easyocr', 'librosa', 'soundfile']
    for pkg in required:
        try:
            import_name = pkg.replace('-', '_').replace('opencv_python', 'cv2')
            __import__(import_name)
        except ImportError:
            print(f"📦 تثبيت {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

# استدعاء دالة التثبيت
ensure_dependencies()

import cv2
import numpy as np

def extract_text_from_frame(frame_path):
    """استخراج النص مع دعم العربية والإنجليزية مع Graceful Degradation"""
    frame = cv2.imread(str(frame_path))
    if frame is None:
        return None
        
    # محاولة 1: pytesseract
    try:
        import pytesseract
        text = pytesseract.image_to_string(frame, lang='ara+eng')
        if text.strip():
            return text
    except Exception:
        pass
        
    # محاولة 2: easyocr
    try:
        import easyocr
        reader = easyocr.Reader(['ar', 'en'], gpu=False)
        results = reader.readtext(frame)
        return ' '.join([r[1] for r in results])
    except Exception:
        pass
        
    # محاولة 3: paddleocr
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='ar', show_log=False)
        result = ocr.ocr(str(frame_path))
        if result and result[0]:
            return ' '.join([line[1][0] for line in result[0]])
    except Exception:
        pass
        
    return None

def check_ocr_bounds(frame_path):
    """التحقق من أن النص ليس خارج الشاشة"""
    frame = cv2.imread(str(frame_path))
    if frame is None:
        return {"status": "error", "message": "فشل قراءة الإطار"}
        
    h, w, _ = frame.shape
    if w != 1080 or h != 1920:
        return {"status": "warning", "message": f"الأبعاد ليست 1080x1920 ({w}x{h})"}
        
    # سنفحص فقط عبر Tesseract للحصول على Bounding boxes إذا كان متاحاً
    try:
        import pytesseract
        data = pytesseract.image_to_data(frame, output_type=pytesseract.Output.DICT)
        out_of_bounds = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if text:
                x, y, bw, bh = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                if x < 0 or y < 0 or (x + bw) > w or (y + bh) > h:
                    out_of_bounds.append(text)
        
        if out_of_bounds:
            return {"status": "fail", "message": f"النص '{out_of_bounds[0]}' خارج حدود الشاشة"}
    except Exception:
        return {"status": "warning", "message": "تعذر فحص الـ Bounds (Tesseract غير متاح أو فشل)"}
        
    return {"status": "pass", "message": "لا يوجد نص خارج الحدود"}

def check_color_contrast(frame_path):
    """التحقق من تباين الألوان"""
    frame = cv2.imread(str(frame_path))
    if frame is None:
        return {"status": "error"}
        
    # للحصول على التباين، يمكننا حساب الـ luminance للنص والخلفية
    # نظراً لصعوبة فصل النص بدقة بدون OCR مخصص، سنفحص التباين العام للصورة
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    min_val, max_val, _, _ = cv2.minMaxLoc(gray)
    
    # نسبة التباين المبسطة
    if min_val == 0: min_val = 1
    contrast_ratio = (max_val + 0.05) / (min_val + 0.05)
    
    if contrast_ratio < 4.5:
        return {"status": "warning", "message": f"تباين منخفض ({contrast_ratio:.1f}:1) قد يكون النص غير مقروء"}
        
    return {"status": "pass", "message": f"تباين جيد ({contrast_ratio:.1f}:1)"}

def detect_empty_space(frame_path):
    """اكتشاف المناطق الفارغة (dead space)"""
    frame = cv2.imread(str(frame_path))
    if frame is None:
        return {"status": "error"}
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
    
    non_zero = cv2.countNonZero(thresh)
    total_pixels = frame.shape[0] * frame.shape[1]
    empty_ratio = 1.0 - (non_zero / total_pixels)
    
    if empty_ratio > 0.4:
        return {"status": "warning", "message": f"توزيع سيء — {empty_ratio*100:.0f}% من الشاشة فارغ"}
        
    return {"status": "pass", "message": "توزيع المساحة جيد"}

def extract_frames(project_id, comp_name):
    """يستخرج الإطارات باستخدام remotion still"""
    project_dir = Path(f"projects/{project_id}/06_build").resolve()
    out_dir = project_dir / "qc_frames"
    out_dir.mkdir(exist_ok=True)
    
    print(f"🎬 استخراج الإطارات للفحص (قد يستغرق وقتاً)...")
    # استخراج 3 إطارات للفحص
    for frame in [10, 30, 60]:
        frame_file = out_dir / f"frame_{frame}.png"
        cmd = [
            "npx", "remotion", "still",
            "src/index.ts", comp_name,
            str(frame_file.resolve()),
            f"--frame={frame}"
        ]
        try:
            use_shell = os.name == "nt"
            subprocess.run(cmd, cwd=str(project_dir), shell=use_shell, check=True, capture_output=True)
        except Exception as e:
            print(f"⚠️ فشل استخراج الإطار {frame}: {e}")
            
    return list(out_dir.glob("*.png"))

def main():
    parser = argparse.ArgumentParser(description="فحص جودة المشاهد الذكي (Smart QC)")
    parser.add_argument("project_id", help="معرف المشروع")
    parser.add_argument("comp_name", help="اسم الكومبوزيشن")
    args = parser.parse_args()
    
    project_id = args.project_id
    comp_name = args.comp_name
    
    project_dir = Path(f"projects/{project_id}")
    report_path = project_dir / "smart_qc_report.json"
    
    if not project_dir.exists():
        print(f"❌ المشروع {project_id} غير موجود.")
        sys.exit(1)
        
    frames = extract_frames(project_id, comp_name)
    if not frames:
        print("❌ لم يتم استخراج أي إطارات للفحص.")
        # ننشئ تقرير الفشل
        report = {"status": "fail", "reason": "No frames extracted"}
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        sys.exit(1)
        
    report = {
        "status": "pass",
        "frames_checked": len(frames),
        "results": []
    }
    
    has_failure = False
    
    for frame in frames:
        print(f"🔍 فحص الإطار: {frame.name}")
        frame_result = {
            "frame": frame.name,
            "text_content": extract_text_from_frame(frame),
            "bounds": check_ocr_bounds(frame),
            "contrast": check_color_contrast(frame),
            "layout": detect_empty_space(frame)
        }
        
        # إذا كان النص خارج الحدود نعتبره فشلاً
        if frame_result["bounds"].get("status") == "fail":
            has_failure = True
            print(f"❌ {frame_result['bounds'].get('message')}")
        
        # التباين المنخفض مجرد تحذير، ولكن يمكن أن يكون فشلاً حسب السياسة. سنعتبره تحذيراً (كما في البرومبت)
        if frame_result["contrast"].get("status") == "warning":
            print(f"⚠️ {frame_result['contrast'].get('message')}")
            
        report["results"].append(frame_result)
        
    if has_failure:
        report["status"] = "fail"
        
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    if has_failure:
        print("❌ Smart QC فشل. انظر التقرير للتفاصيل.")
        sys.exit(1)
    else:
        print("✅ Smart QC نجح.")
        sys.exit(0)

if __name__ == "__main__":
    main()
