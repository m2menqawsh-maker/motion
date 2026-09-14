# -*- coding: utf-8 -*-
"""code_template_gate.py — يمنع الارتجال ويجبر الوكيل على استخدام القوالب
Usage: python code_template_gate.py <project_dir>"""
import sys, json, re, hashlib, subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def verify_git_integrity():
    try:
        # Check if there are any untracked, modified, or deleted files in templates/
        result = subprocess.run(['git', 'status', '--porcelain', 'templates/'], 
                                capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print("\n" + "="*60)
            print("🛑 CRITICAL: تم اكتشاف عبث في مجلد القوالب الأساسية! (Git Integrity Lock)")
            print("="*60)
            print("الملفات المتضررة:")
            print(result.stdout)
            print("❌ يُمنع منعاً باتاً تعديل القوالب الأساسية. يرجى التراجع عن التعديلات (git restore) قبل السماح بالاستمرار.")
            sys.exit(1)
    except Exception as e:
        # If git fails for some reason not related to status, we log it but don't hard crash unless we want to be paranoid
        pass

def verify_local_templates_integrity(proj_path):
    proj = Path(proj_path).resolve()
    ws_dir = Path(__file__).resolve().parent.parent
    local_tpl_dir = proj / "06_build" / "src" / "templates"
    
    if not local_tpl_dir.exists():
        return
        
    for local_file in local_tpl_dir.rglob("*.tsx"):
        rel_path = local_file.relative_to(local_tpl_dir)
        source_file = ws_dir / "templates" / rel_path
        
        if not source_file.exists():
            print("\n" + "="*60)
            print("🛑 CRITICAL: قالب محلي مزيف! (Local Template Hallucination Lock)")
            print("="*60)
            print(f"الملف الوهمي: {local_file}")
            print("❌ الوكيل قام بإنشاء قالب محلي من العدم داخل مجلد البناء. هذا ارتجال مرفوض!")
            sys.exit(1)
            
        with open(local_file, "rb") as f1, open(source_file, "rb") as f2:
            h1 = hashlib.md5(f1.read()).hexdigest()
            h2 = hashlib.md5(f2.read()).hexdigest()
            
        if h1 != h2:
            print("\n" + "="*60)
            print("🛑 CRITICAL: تلاعب في قالب محلي! (Local Template Tamper Lock)")
            print("="*60)
            print(f"الملف المتضرر: {local_file}")
            print(f"الملف الأصلي المرجعي: {source_file}")
            print("❌ الوكيل قام بتعديل القالب يدوياً داخل مجلد البناء (Backdoor Tampering). يُمنع منعاً باتاً تعديل القوالب، استخدم تمرير البيانات props فقط!")
            sys.exit(1)

def run_gate(proj_path):
    verify_git_integrity()
    verify_local_templates_integrity(proj_path)
    
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
            
    # 1.1 Check for ad-hoc code generators in scratch/
    ws_dir = Path(__file__).resolve().parent.parent
    scratch_dir = ws_dir / "scratch"
    if scratch_dir.exists():
        for py_file in scratch_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "import React" in content or ".tsx" in content or "Hash:" in content:
                    fails.append(f"FAIL: ملف مشبوه لتوليد الكود في مجلد scratch: {py_file.name}. يُمنع كتابة مولدات كود للالتفاف على البوابات!")
            except Exception:
                pass
            
    # Load blueprint templates
    bp_templates = set()
    if bp_file.exists():
        try:
            bp = json.loads(bp_file.read_text(encoding="utf-8"))
            for sec in bp.get("timeline", []):
                for e in sec.get("elements", []):
                    if e.get("kind") == "template":
                        tpl = e.get("template")
                        bp_templates.add(tpl)
                        
            # V1 Checking
            for scene in bp.get("scenes", []):
                tpl = scene.get("template")
                if tpl: 
                    bp_templates.add(tpl)
                if tpl == "terminal-simulator":
                    surface = scene.get("surface", {})
                    content = scene.get("content", {})
                    lines = content.get("lines", [])
                    stext = surface.get("text", "")
                    if not lines:
                        fails.append(f"FAIL: 'terminal-simulator' requires 'content.lines' array in {scene.get('scene_id')}. Cannot be empty.")
                    elif len(lines) == 1 and lines[0] == stext:
                        fails.append(f"FAIL: 'terminal-simulator' in {scene.get('scene_id')} has duplicate content.lines! You must provide actual log outputs.")
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
                
            # فحص صارم: هل تم تمرير البيانات للقوالب؟ (Data-Driven Check)
            if has_template_or_engine:
                if 'surface=' not in content and 'surface={' not in content and '{...surface}' not in content:
                    fails.append(f"FAIL: ملف مشهد لا يمرر بيانات surface للقوالب (Data-Driven Violation): {rel_path}")
                if 'animation=' not in content and 'animation={' not in content and not re.search(r'surface=\{.*?animation', content, re.DOTALL):
                    # We only warn for animation as it might be bundled inside surface, but we check if it's explicitly passed or extracted.
                    pass # Not strictly failing for animation if surface is passed, but we enforce surface.
                
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
