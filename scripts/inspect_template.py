import subprocess
from scripts.security import safe_subprocess
import sys
from scripts.path_security import validate_project_id, safe_resolve
import os
import re

def find_template(name):
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.lower() == f"{name.lower()}.tsx":
                return os.path.join(root, file)
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_template.py <TemplateName>")
        return
        
    template_name = sys.argv[1]
    if not template_name.lower().endswith("wrapper"):
        template_name += "wrapper"
        
    path = find_template(template_name)
    if not path:
        print(f"Error: Could not find template '{template_name}' in templates/ directory.")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Extract surface properties
    surface_props = set(re.findall(r'surface\?\.([a-zA-Z0-9_]+)', content))
    
    # Extract content properties
    content_props = set(re.findall(r'content\?\.([a-zA-Z0-9_]+)', content))
    
    # Check for content.lines directly
    if 'content.lines' in content or 'content?.lines' in content:
        content_props.add('lines')
        
    # Check for content.text directly
    if 'content.text' in content or 'content?.text' in content:
        content_props.add('text')
        
    # Check if it uses template_props
    uses_template_props = 'template_props' in content
    
    print(f"\n🔍 Template Schema for: {os.path.basename(path)}")
    print("-" * 40)
    print("When writing 05_blueprint.json, you MUST provide these properties if applicable:\n")
    
    if surface_props:
        print("▶ [surface] object should contain:")
        for prop in sorted(surface_props):
            print(f"   - {prop}")
    else:
        print("▶ [surface] object: Not explicitly required or used dynamically.")
        
    print()
    if content_props:
        print("▶ [content] object should contain:")
        for prop in sorted(content_props):
            print(f"   - {prop}")
    else:
        print("▶ [content] object: Not explicitly required or used dynamically.")
        
    print()
    if uses_template_props:
        print("▶ [template_props] object:")
        print("   - This template supports custom overrides via template_props.")
    
    print("\n✅ End of Schema\n")

if __name__ == '__main__':
    main()
