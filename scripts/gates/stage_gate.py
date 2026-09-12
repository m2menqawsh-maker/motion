import os
import sys
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import validate, ValidationError
from checks import check_gate_1, check_gate_2, check_gate_3

def get_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_schema(schema_name: str) -> dict:
    p = Path(f"schemas/{schema_name}")
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

class StateManager:
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.state_path = self.project_dir / "state.json"
        self.schema = load_schema("state.schema.json")
        self.state = self._load()

    def _load(self) -> dict:
        if not self.state_path.exists():
            print(f"❌ state.json not found in {self.project_dir}")
            sys.exit(1)
        with open(self.state_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save(self):
        self.state["updated_at"] = get_now()
        
        try:
            validate(instance=self.state, schema=self.schema)
        except ValidationError as e:
            print(f"❌ خطأ برمجي: حالة غير صالحة برمجياً!\n{e.message}")
            sys.exit(2)
            
        temp_path = self.state_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, self.state_path)

    def status(self):
        print("حالة المشروع:")
        print(f"المرحلة الحالية: {self.state.get('current_stage', 0)}")
        stages = self.state.get("stages", {})
        gates = self.state.get("gates", {})
        
        for k, v in stages.items():
            print(f"  Stage {k}: {v.get('status')}")
            
        print("\nحالة البوابات:")
        for k, v in gates.items():
            print(f"  {k}: {v.get('status', 'locked')} (بواسطة: {v.get('approved_by', 'N/A')})")

    def start(self, stage: str):
        stages = self.state.setdefault("stages", {})
        gates = self.state.setdefault("gates", {})
        
        if stage == "0":
            if stages.get("0", {}).get("status") not in ["pending", "failed"]:
                print("❌ لا يمكن بدء المرحلة 0 لأنها ليست pending أو failed.")
                sys.exit(1)
        elif stage == "1":
            if gates.get("gate_1", {}).get("status") != "approved":
                print("❌ لا يمكن بدء المرحلة 1: البوابة 1 غير معتمدة.")
                sys.exit(1)
        elif stage == "2":
            if gates.get("gate_2", {}).get("status") != "approved":
                print("❌ لا يمكن بدء المرحلة 2: البوابة 2 غير معتمدة.")
                sys.exit(1)
        elif stage == "3":
            if gates.get("gate_3", {}).get("status") != "approved":
                print("❌ لا يمكن بدء المرحلة 3: البوابة 3 غير معتمدة.")
                sys.exit(1)
        else:
            print(f"❌ مرحلة غير معروفة: {stage}")
            sys.exit(1)
            
        if stage not in stages:
            stages[stage] = {}
        stages[stage]["status"] = "running"
        stages[stage]["started_at"] = get_now()
        self.state["current_stage"] = int(stage)
        self._save()
        print(f"✅ تم بدء المرحلة {stage} بنجاح.")

    def finish(self, stage: str):
        stages = self.state.setdefault("stages", {})
        gates = self.state.setdefault("gates", {})
        
        if stages.get(stage, {}).get("status") != "running":
            print(f"❌ لا يمكن إنهاء المرحلة {stage} لأنها ليست قيد التشغيل.")
            sys.exit(1)
            
        stages[stage]["status"] = "done"
        stages[stage]["finished_at"] = get_now()
        
        # Open next gate
        if stage == "0":
            if "gate_1" not in gates: gates["gate_1"] = {}
            gates["gate_1"]["status"] = "awaiting"
        elif stage == "1":
            if "gate_2" not in gates: gates["gate_2"] = {}
            gates["gate_2"]["status"] = "awaiting"
        elif stage == "2":
            if "gate_3" not in gates: gates["gate_3"] = {}
            gates["gate_3"]["status"] = "awaiting"
        
        self._save()
        print(f"✅ تم إنهاء المرحلة {stage} بنجاح.")

    def fail(self, stage: str, error: str):
        stages = self.state.setdefault("stages", {})
        if stages.get(stage, {}).get("status") != "running":
            print(f"❌ لا يمكن إفشال المرحلة {stage} لأنها ليست قيد التشغيل.")
            sys.exit(1)
            
        stages[stage]["status"] = "failed"
        self.state["last_error"] = error
        self._save()
        print(f"🛑 فشلت المرحلة {stage}: {error}")

    def approve(self, gate_num: str, by: str, note: str = ""):
        gates = self.state.setdefault("gates", {})
        gate_key = f"gate_{gate_num}"
        gate_val = gates.get(gate_key, {"status": "locked"})
        status = gate_val.get("status", "locked")
        
        if status not in ["locked", "awaiting", "rejected"]:
            print(f"❌ لا يمكن اعتماد {gate_key} لأن حالتها الحالية: {status}")
            sys.exit(1)
            
        if gate_num == "1":
            res = check_gate_1(str(self.project_dir))
            if not res["ok"]:
                print(f"❌ فشل فحص البوابة 1:\n" + "\n".join(res["errors"]))
                sys.exit(1)
        elif gate_num == "2":
            g1_val = gates.get("gate_1", {"status": "locked"})
            if g1_val.get("status") != "approved":
                print("❌ لا يمكن اعتماد البوابة 2 لأن البوابة 1 غير معتمدة.")
                sys.exit(1)
            res = check_gate_2(str(self.project_dir))
            if not res["ok"]:
                print(f"❌ فشل فحص البوابة 2:\n" + "\n".join(res["errors"]))
                sys.exit(1)
        elif gate_num == "3":
            g2_val = gates.get("gate_2", {"status": "locked"})
            if g2_val.get("status") != "approved":
                print("❌ لا يمكن اعتماد البوابة 3 لأن البوابة 2 غير معتمدة.")
                sys.exit(1)
            res = check_gate_3(str(self.project_dir))
            if not res["ok"]:
                print(f"❌ فشل فحص البوابة 3:\n" + "\n".join(res["errors"]))
                sys.exit(1)
        else:
            print(f"❌ رقم بوابة غير صحيح: {gate_num}")
            sys.exit(1)
            
        gate_val["status"] = "approved"
        gate_val["approved_by"] = by
        gate_val["approved_at"] = get_now()
        if note:
            gate_val["note"] = note # note instead of notes per schema
            
        gates[gate_key] = gate_val
        self._save()
        print(f"✅ تم اعتماد البوابة {gate_num} بنجاح.")

    def reject(self, gate_num: str, by: str, note: str):
        gates = self.state.setdefault("gates", {})
        gate_key = f"gate_{gate_num}"
        gate_val = gates.get(gate_key, {"status": "locked"})
        status = gate_val.get("status", "locked")
        
        if status not in ["awaiting", "rejected"]:
            print(f"❌ لا يمكن رفض {gate_key} لأن حالتها: {status}")
            sys.exit(1)
            
        gate_val["status"] = "rejected"
        gate_val["note"] = note
        gates[gate_key] = gate_val
        self._save()
        print(f"🛑 تم رفض البوابة {gate_num}: {note}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python stage_gate.py <project_dir> <command> [args]")
        sys.exit(1)
        
    project_dir = sys.argv[1]
    cmd = sys.argv[2]
    
    manager = StateManager(project_dir)
    
    if cmd == "status":
        manager.status()
    elif cmd == "start":
        if len(sys.argv) < 4:
            print("Usage: ... start <n>")
            sys.exit(1)
        manager.start(sys.argv[3])
    elif cmd == "finish":
        if len(sys.argv) < 4:
            print("Usage: ... finish <n>")
            sys.exit(1)
        manager.finish(sys.argv[3])
    elif cmd == "fail":
        if len(sys.argv) < 5:
            print("Usage: ... fail <n> <error>")
            sys.exit(1)
        manager.fail(sys.argv[3], sys.argv[4])
    elif cmd == "approve":
        if len(sys.argv) < 5:
            print("Usage: ... approve <1|2|3> <by> [note]")
            sys.exit(1)
        note = sys.argv[5] if len(sys.argv) > 5 else ""
        manager.approve(sys.argv[3], sys.argv[4], note)
    elif cmd == "reject":
        if len(sys.argv) < 6:
            print("Usage: ... reject <1|2|3> <by> <note>")
            sys.exit(1)
        manager.reject(sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
