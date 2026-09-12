import os
import glob
import re

plugin_root = r"c:\video\clean-video-workspace\.agents\plugins\super-video-maker-plugin"
index_file = os.path.join(plugin_root, "references", "deep", "ground-truth", "TEMPLATE_INDEX.md")

disk_basenames = {}
for d in ["premium-templates", r"remotion-app\src"]:
    pattern = os.path.join(plugin_root, d, "**", "*.tsx")
    for f in glob.glob(pattern, recursive=True):
        basename = os.path.basename(f)
        disk_basenames[basename] = f

index_basenames = set()
if os.path.exists(index_file):
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
        paths = re.findall(r'\]\((.*?\.tsx)\)|(.*?\.tsx)', content)
        for p in paths:
            path = p[0] or p[1]
            index_basenames.add(os.path.basename(path))

on_disk_not_in_index = set(disk_basenames.keys()) - index_basenames
in_index_not_on_disk = index_basenames - set(disk_basenames.keys())
matching = set(disk_basenames.keys()).intersection(index_basenames)

print("=== On disk but NOT in index (potential orphans) ===")
for f in sorted(list(on_disk_not_in_index)):
    print(disk_basenames[f].replace(plugin_root, ''))
print("\n=== In index but NOT on disk (broken links) ===")
for f in sorted(list(in_index_not_on_disk)):
    print(f)
print(f"\n=== Matching count: {len(matching)} ===")
