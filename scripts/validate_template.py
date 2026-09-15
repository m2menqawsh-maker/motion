import os
import sys
import re

def validate_template(file_path):
    print(f"🔍 Validating Custom Template: {file_path}...")
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File {file_path} does not exist.")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    errors = []

    # 1. Check for standard props extraction
    if not re.search(r'surface', content) or not re.search(r'content', content) or not re.search(r'template_props', content):
        errors.append("Template must accept { surface, content, template_props } as props.")

    # 2. Check for Zod schema export
    if not re.search(r'export\s+const\s+schema\s*=', content):
        errors.append("Template must export a 'schema' (e.g. export const schema = z.object({...})) to define its template_props.")

    if errors:
        print("❌ Validation Failed. Please fix the following issues:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print(f"✅ Template {file_path} passed structural validation.")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_template.py <path_to_tsx>")
        sys.exit(1)
    
    success = validate_template(sys.argv[1])
    if not success:
        sys.exit(1)
