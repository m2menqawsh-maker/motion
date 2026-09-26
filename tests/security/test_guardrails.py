import os
import sys
import json
import unittest
import tempfile
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(os.path.abspath(__file__)).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gates.plan_gate import validate_plan_quality

class TestGuardrails(unittest.TestCase):
    
    def test_plan_gate_padding(self):
        # 1. Test padding rejection
        bad_plan = "#### المشهد 1\n<!--   padding   -->\n- القالب: Template1\n- SFX: swoosh.wav\n| الكلمة | التوقيت |\n motion_taste_citation treatment_citation"
        is_valid, errors = validate_plan_quality(bad_plan)
        self.assertFalse(is_valid)
        self.assertTrue(any("padding" in err.lower() or "حشو" in err for err in errors))
        
    def test_plan_gate_templates(self):
        # 2. Test template diversity
        # 1 scene -> 1 template (Should pass)
        plan_1_scene = "#### المشهد 1\n- القالب: Template1\n- SFX: swoosh.wav\n| الكلمة | التوقيت |\nmotion_taste_citation treatment_citation"
        is_valid, errors = validate_plan_quality(plan_1_scene)
        self.assertTrue(is_valid, f"Expected 1 scene 1 template to pass, got errors: {errors}")
        
        # 3 scenes -> 1 template (Should fail)
        plan_3_scenes_1_template = """
        #### المشهد 1
        - القالب: Template1
        | الكلمة |
        #### المشهد 2
        - القالب: Template1
        | الكلمة |
        #### المشهد 3
        - القالب: Template1
        | الكلمة |
        motion_taste_citation treatment_citation
        """
        is_valid, errors = validate_plan_quality(plan_3_scenes_1_template)
        self.assertFalse(is_valid)
        self.assertTrue(any("قوالب" in err for err in errors))
        
    def test_violations_config_regexes(self):
        import re
        config_path = PROJECT_ROOT / "config" / "violations_config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        command_rules = config.get("command_violations", [])
        npm_rule = next(r for r in command_rules if "npx" in r["pattern"])
        
        # Test exact match
        self.assertTrue(re.search(npm_rule["pattern"], "npx remotion render", re.IGNORECASE))
        self.assertTrue(re.search(npm_rule["pattern"], "npm run studio", re.IGNORECASE))
        # Test newline evasion
        self.assertTrue(re.search(npm_rule["pattern"], "npx\nremotion", re.IGNORECASE))
        # Test multiple spaces
        self.assertTrue(re.search(npm_rule["pattern"], "npm   run", re.IGNORECASE))
        
        # Test safe commands (should not match)
        self.assertFalse(re.search(npm_rule["pattern"], "open_studio.py npm_run", re.IGNORECASE))

if __name__ == "__main__":
    unittest.main()
