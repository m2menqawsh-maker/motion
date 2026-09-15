import subprocess
from scripts.security import safe_subprocess
import json
import hashlib
from pathlib import Path
from jsonschema import validate, ValidationError

# Unified Gate System

class GateViolation(Exception):
    def __init__(self, rule: str, reason: str, fix: str):
        self.rule = rule
        self.reason = reason
        self.fix = fix
        super().__init__(f"[{rule}] {reason}\n🔧 الإصلاح: {fix}")

class ProjectGates:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = Path(f"projects/{project_id}")
        if not self.project_dir.exists():
            raise GateViolation("PROJECT_NOT_FOUND", f"المشروع '{project_id}' غير موجود", f"أنشئ المشروع في projects/{project_id}")

    def verify_plan_exists(self):
        """Standardized check for master_plan.md"""
        plan = self.project_dir / "master_plan.md"
            
        if not plan.exists() or plan.stat().st_size == 0:
            raise GateViolation("PLAN_MISSING", "ملف master_plan.md غير موجود أو فارغ", "اكتب خطة المشروع أولاً")

    def verify_blueprint_schema(self) -> dict:
        """Validates 05_blueprint.json against the generated Zod schema (JSON Schema)"""
        bp_path = self.project_dir / "05_blueprint.json"
            
        if not bp_path.exists():
            raise GateViolation("BLUEPRINT_MISSING", "ملف 05_blueprint.json غير موجود", "قم بتوليد المخطط أولاً")
            
        try:
            bp_data = json.loads(bp_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise GateViolation("BLUEPRINT_INVALID_JSON", "ملف 05_blueprint.json ليس بصيغة JSON صحيحة", "أصلح صياغة الملف")

        schema_path = Path("schemas/blueprint.schema.json")
        if schema_path.exists():
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            try:
                validate(instance=bp_data, schema=schema)
            except ValidationError as e:
                raise GateViolation("BLUEPRINT_SCHEMA_VIOLATION", f"مخالفة في المخطط: {e.message}", f"عدل الحقل {e.json_path} ليطابق المواصفات")
        else:
            print("تحذير: schemas/blueprint.schema.json غير موجود. يرجى توليده بواسطة npx tsx scripts/generate_schema.ts")

        # Custom V2 validation carried over
        self._validate_v2_features(bp_data)
        
        return bp_data

    def _validate_v2_features(self, bp: dict):
        """Preserves legacy V2 timeline timeline features now integrated into scenes"""
        PERSONA_EXACT = {
            "Cinematic": {"duration_min": 350, "duration_max": 600},
            "Energetic": {"duration_min": 100, "duration_max": 250},
            "Playful":   {"duration_min": 150, "duration_max": 300},
            "Technical": {"duration_min": 200, "duration_max": 400}
        }
        
        persona = bp.get("meta", {}).get("motion_personality", "Cinematic")
        bounds = PERSONA_EXACT.get(persona, PERSONA_EXACT["Cinematic"])
        
        total_duration = sum(s.get("durationFrames", 0) for s in bp.get("scenes", []))
        
        # Note: Remotion fps is usually 30. Duration in seconds = frames / 30.
        # However V2 bounds were likely in frames or seconds, we assume frames if min is 100.
        # Actually V2 duration bounds were likely frames based on their values (100 to 600 frames = 3 to 20 seconds).
        if not (bounds["duration_min"] <= total_duration <= bounds["duration_max"]):
            raise GateViolation("PERSONA_DURATION_VIOLATION", 
                f"المدة الكلية {total_duration} إطار لا تطابق شخصية {persona} ({bounds['duration_min']}-{bounds['duration_max']})", 
                "عدل durationFrames في المشاهد لتناسب الشخصية"
            )
            
        for i, scene in enumerate(bp.get("scenes", [])):
            layout = scene.get("layout", {})
            layer = layout.get("layer")
            if layer is not None and not (1 <= layer <= 5):
                raise GateViolation("LAYER_VIOLATION", f"المشهد {i} يحتوي على layer {layer} خارج النطاق 1-5", "عدل layer")
                
            cov = layout.get("coverage_pct")
            if cov is not None and not (0 <= cov <= 100):
                raise GateViolation("COVERAGE_VIOLATION", f"المشهد {i} التغطية {cov} خارج النطاق 0-100", "عدل coverage_pct")

def calculate_deep_hash(project_id: str, bp_data: dict, build_dir: Path) -> str:
    """Calculates a deep SHA-256 hash representing the absolute exact state of the project"""
    # In a real implementation we would hash the media contents (mp4/png) inside build_dir/media, 
    # the exact templates used, and all config JSONs.
    hasher = hashlib.sha256()
    
    project_dir = Path(f"projects/{project_id}")
    
    # 1. Hash Configs
    for file in ["05_blueprint.json", "manifest.json", "brand.json", "project.json"]:
        p = project_dir / file
        if p.exists():
            hasher.update(p.read_bytes())
            
    # 2. Hash Media in build_dir
    media_dir = build_dir / "public" / "media"
    if media_dir.exists():
        for f in sorted(media_dir.glob("*.*")):
            if f.is_file():
                hasher.update(f.read_bytes())
                
    # 3. Hash Templates used in Blueprint
    for scene in bp_data.get("scenes", []):
        tpl = scene.get("template")
        tpl_path = Path(f"remotion-app/src/templates/{tpl}.tsx") # Example path
        if tpl_path.exists():
            hasher.update(tpl_path.read_bytes())
            
    return hasher.hexdigest()
