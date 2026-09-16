import re

filepath = 'registry/template-registry.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The file looks like:
# "rui-t-h-e-m-e-s": { ... },
# "rui-t-h-e-m-e-s": { ... },

# We can parse the file and keep only the first occurrence of each key.
# A simpler way is to just use regex to find duplicate blocks if they are exact copies.
# Actually, since it's a TS file, let's use a simpler python script to remove duplicates.

def deduplicate_registry(text):
    lines = text.split('\n')
    out_lines = []
    seen_keys = set()
    
    in_block = False
    current_key = None
    block_lines = []
    
    # We are looking for lines like:   "some-id": {
    # inside export const TEMPLATE_REGISTRY: Record<string, TemplateEntry> = {
    
    in_registry = False
    for line in lines:
        if 'export const TEMPLATE_REGISTRY' in line:
            in_registry = True
            out_lines.append(line)
            continue
            
        if in_registry:
            match = re.match(r'^\s*"([^"]+)":\s*\{', line)
            if match:
                current_key = match.group(1)
                in_block = True
                block_lines = [line]
                continue
            
            if in_block:
                block_lines.append(line)
                if re.match(r'^\s*\},?', line):
                    # End of block
                    if current_key not in seen_keys:
                        seen_keys.add(current_key)
                        out_lines.extend(block_lines)
                    else:
                        print(f"Removed duplicate key: {current_key}")
                    in_block = False
                continue
        
        out_lines.append(line)
        
    return '\n'.join(out_lines)

new_content = deduplicate_registry(content)

# We also need to fix duplicate imports!
# import { THEMESWrapper } from "../templates/elements/THEMESWrapper";
def deduplicate_imports(text):
    lines = text.split('\n')
    out_lines = []
    seen_imports = set()
    for line in lines:
        if line.startswith('import '):
            if line in seen_imports:
                continue
            seen_imports.add(line)
        out_lines.append(line)
    return '\n'.join(out_lines)

new_content = deduplicate_imports(new_content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
    
print("Fixed duplicates in template-registry.tsx")
