import os
import re

filepath = 'templates/brand-resolver.ts'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = content.replace('../contracts/brand', '@contracts/brand')
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

filepath = 'remotion-app/src/remotion/lib/map-utils.ts'
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = content.replace('import maplibregl', 'import * as maplibregl')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

filepath = 'remotion-app/src/BlueprintVideo.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix flip() -> flip({} as any)
content = re.sub(r'presentation = ([a-zA-Z0-9_]+)\(\)', r'presentation = \1({} as any)', content)
# Fix let presentation = fade(); -> let presentation: any = fade();
content = content.replace('let presentation = fade();', 'let presentation: any = fade();')
# Fix scene.transition
content = content.replace('scene.transition.type', '(scene as any).transition.type')
content = content.replace('scene.transition &&', '(scene as any).transition &&')
content = content.replace('scene.transition.durationFrames', '(scene as any).transition.durationFrames')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed BlueprintVideo, map-utils, and brand-resolver")
