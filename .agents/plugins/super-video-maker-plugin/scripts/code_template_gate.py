# -*- coding: utf-8 -*-
"""code_template_gate.py — يمنع الارتجال ويجبر الوكيل على استخدام القوالب
Usage: python code_template_gate.py <project_dir>"""
import sys, json, re, hashlib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def run_gate(proj_path):
    proj = Path(proj_path).resolve()
    build_dir = proj / "06_build"
    comps_dir = build_dir / "src" / "compositions"
    bp_file = proj / "05_blueprint.json"
    
    fails = []
    warns = []
    
    # 1. Check for forbidden directories
    for forbidden in ["components/snap-cn", "components/onda"]:
        if (build_dir / "src" / forbidden).exists():
            fails.append(f"FAIL: مجلد {forbidden} محلي داخل 06_build (شادكن ممنوع، استخدم @templates أو @engine)")
            
    # Load blueprint templates
    bp_templates = set()
    if bp_file.exists():
        try:
            bp = json.loads(bp_file.read_text(encoding="utf-8"))
            for sec in bp.get("timeline", []):
                for e in sec.get("elements", []):
                    if e.get("kind") == "template":
                        bp_templates.add(e.get("template"))
        except Exception as e:
            fails.append(f"FAIL: خطأ في قراءة 05_blueprint.json: {e}")
            
    # 2. Check TSX files
    all_imports = set()
    
    if comps_dir.exists():
        for tsx_file in comps_dir.rglob("*.tsx"):
            rel_comps = tsx_file.relative_to(comps_dir)
            
            try:
                content = tsx_file.read_text(encoding="utf-8")
            except Exception:
                continue
                
            # ─── استثناء: الكود في مجلد custom/ ───
            if rel_comps.parts[0] == "custom":
                if '/* CUSTOM CODE' not in content:
                    fails.append(f"FAIL: {rel_comps}: الكود المخصص يجب أن يحتوي على توثيق /* CUSTOM CODE ... */")
                continue
                
            if rel_comps.parts[0] != "generated":
                fails.append(f"FAIL: ملف .tsx خارج مجلد generated/ (ممنوع): {rel_comps}")
                
            # Verify Hash
            if rel_comps.parts[0] == "generated":
                if "// GENERATED — DO NOT EDIT" not in content:
                    fails.append(f"FAIL: ملف مولّد مفقود ترويسة GENERATED: {rel_comps}")
                else:
                    match = re.search(r'// Hash: ([a-f0-9]+)', content)
                    if match:
                        expected_hash = match.group(1)
                        parts = content.split('\n', 2)
                        if len(parts) >= 3:
                            raw_content = parts[2]
                            if hashlib.md5(raw_content.encode('utf-8')).hexdigest() != expected_hash:
                                fails.append(f"FAIL: تم تعديل الملف يدوياً (Hash mismatch): {rel_comps}")
                    else:
                        fails.append(f"FAIL: ملف مولّد مفقود الهاش: {rel_comps}")
                        
            # فحص: هل يحتوي على كود حركة محظور؟
            banned_patterns = [
                'spring(',
                'interpolate(',
                'useCurrentFrame(',
            ]
            for pattern in banned_patterns:
                if pattern in content:
                    fails.append(f"FAIL: {rel_comps}: يحتوي على '{pattern}' (ممنوع خارج القوالب/الكود المخصص)")


                
            # Extract import statements
            import_lines = re.findall(r'^import\s+.*?(?:from\s+)?[\'"](.*?)[\'"]', content, re.MULTILINE)
            
            has_template_or_engine = False
            template_import_count = 0
            
            for imp in import_lines:
                if any(x in imp for x in ["@templates", "@engine", "../templates", "../engine", "../../templates", "../../engine"]):
                    has_template_or_engine = True
                    template_import_count += 1
            
            rel_path = tsx_file.relative_to(build_dir)
            if not has_template_or_engine:
                fails.append(f"FAIL: ملف مشهد بدون import من @templates أو @engine: {rel_path}")
            
            if template_import_count > 3:
                warns.append(f"WARN: مشهد يستورد أكثر من 3 قوالب ({template_import_count}): {rel_path}")
                
            # Collect potential template names from content for blueprint check
            for t in bp_templates:
                # We check if the template name appears anywhere in the file content
                if t in content:
                    all_imports.add(t)
                    
    # 3. Check if blueprint templates are missing from code
    if comps_dir.exists():
        for t in bp_templates:
            if t not in all_imports:
                fails.append(f"FAIL: قالب '{t}' مذكور في 05_blueprint.json بدون import مطابق في الكود")
            
    if warns:
        for w in warns:
            print(w)
            
    if fails:
        for f in fails:
            print(f)
        sys.exit(1)
        
    print("PASS: جميع المشاهد تلتزم بقواعد القوالب ولا يوجد ارتجال.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    run_gate(sys.argv[1])
