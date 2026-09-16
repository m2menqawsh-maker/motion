import os
import re

files = [
    'templates/elements/BRollStackWrapper.tsx',
    'templates/elements/ChatToPreviewWrapper.tsx',
    'templates/elements/FaqAccordionWrapper.tsx',
    'templates/scenes/MediaSequenceWrapper.tsx'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(r'map\(i =>', r'map((i: any) =>', content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
