#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
from pathlib import Path

def ensure_dependencies():
    """تثبيت المكتبات المطلوبة تلقائياً"""
    required = ['librosa', 'soundfile', 'numpy']
    for pkg in required:
        try:
            import_name = pkg.replace('-', '_')
            __import__(import_name)
        except ImportError:
            print(f"📦 تثبيت {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

ensure_dependencies()

def check_vo_quality(audio_path: str) -> dict:
    import librosa
    import numpy as np
    
    try:
        y, sr = librosa.load(audio_path, sr=None)
        
        # 1. معدل العينة (Sample Rate)
        sr_status = "pass" if sr >= 44100 else "warning"
        
        # 2. Clipping
        max_amp = np.max(np.abs(y))
        clipping_status = "pass" if max_amp < 0.99 else "fail"
        
        # 3. Noise Floor (متوسط الطاقة في أهدأ 10%)
        rms = librosa.feature.rms(y=y)[0]
        sorted_rms = np.sort(rms)
        noise_floor = np.mean(sorted_rms[:max(1, len(sorted_rms)//10)])
        # Threshold estimate for high noise
        noise_status = "pass" if noise_floor < 0.05 else "warning"
        
        return {
            "sample_rate": {"value": sr, "status": sr_status},
            "clipping": {"value": float(max_amp), "status": clipping_status},
            "noise_floor": {"value": float(noise_floor), "status": noise_status},
            "status": "pass" if (sr_status != "fail" and clipping_status != "fail") else "fail"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: python vo_quality_check.py <audio_file>")
        sys.exit(1)
    
    res = check_vo_quality(sys.argv[1])
    import json
    print(json.dumps(res, indent=2))
