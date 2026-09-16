import os
import re

files = [
    'remotion-app/src/templates/elements/BRollStackWrapper.tsx',
    'remotion-app/src/templates/elements/ChatToPreviewWrapper.tsx',
    'remotion-app/src/templates/elements/FaqAccordionWrapper.tsx',
    'remotion-app/src/templates/scenes/MediaSequenceWrapper.tsx'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace (item, i) with (item: any, i: number)
    new_content = re.sub(r'\(([^,]+),\s*i\)\s*=>', r'(\1: any, i: number) =>', content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
