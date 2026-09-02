import re
with open(r'c:\video\clean-video-workspace\.agents\plugins\super-video-maker-plugin\remotion-app\src\Root.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
comps = re.findall(r'<Composition[^>]*id=["\']([^"\']+)["\']', text)
for c in comps: print(c)
