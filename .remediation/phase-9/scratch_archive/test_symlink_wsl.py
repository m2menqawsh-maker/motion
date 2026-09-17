import sys
from pathlib import Path
import tempfile
import os

# Add workspace to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.path_security import safe_resolve

def main():
    tmp_dir = Path(tempfile.mkdtemp())
    base_dir = tmp_dir / "base"
    base_dir.mkdir()
    secret_file = tmp_dir / "secret.txt"
    secret_file.write_text("top secret")
    symlink_path = base_dir / "malicious_link"
    
    os.symlink(str(secret_file), str(symlink_path))
    print("Created symlink successfully in environment.")
    
    try:
        safe_resolve(base_dir, "malicious_link")
        print("FAIL: safe_resolve should have raised ValueError!")
        sys.exit(1)
    except ValueError as e:
        print(f"PASS: symlink attack blocked as expected: {e}")
        sys.exit(0)

if __name__ == "__main__":
    main()
