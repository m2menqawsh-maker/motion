import os
import re

directory = 'remotion-app/src/templates/effects'
for filename in os.listdir(directory):
    if filename.endswith('Transition.tsx'):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace presentation={func()} with presentation={func({} as any)}
        # e.g. presentation={bookFlip()} -> presentation={bookFlip({} as any)}
        new_content = re.sub(r'presentation=\{([a-zA-Z0-9_]+)\(\)\}', r'presentation={\1({} as any)}', content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed {filename}")
