import os, glob, re
plugin_root = r'c:\video\clean-video-workspace\.agents\plugins\super-video-maker-plugin'
src_dir = os.path.join(plugin_root, 'remotion-template', 'src')

all_files = set()
for pattern in ['**/*.tsx', '**/*.ts']:
    for f in glob.glob(os.path.join(src_dir, pattern), recursive=True):
        rel_path = os.path.relpath(f, src_dir).replace('\\', '/')
        all_files.add(rel_path)

imported_files = set()
for f in glob.glob(os.path.join(src_dir, '**/*.*'), recursive=True):
    if f.endswith(('.ts', '.tsx')):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            imports = re.findall(r'from\s+[\"\']([^\"\']+)[\"\']', content)
            imports += re.findall(r'import\s+[\"\']([^\"\']+)[\"\']', content)
            file_dir = os.path.dirname(f)
            for imp in imports:
                if not imp.startswith('.') and not imp.startswith('@/'): continue
                if imp.startswith('@/'):
                    imp_rel = imp.replace('@/', '')
                else:
                    abs_imp = os.path.normpath(os.path.join(file_dir, imp))
                    imp_rel = os.path.relpath(abs_imp, src_dir).replace('\\', '/')
                imported_files.add(imp_rel)

all_files_no_ext = {re.sub(r'(\.tsx|\.ts)$', '', f): f for f in all_files}
all_files_no_ext.update({re.sub(r'/index(\.tsx|\.ts)$', '', f): f for f in all_files if f.endswith('index.tsx') or f.endswith('index.ts')})

matched_imports = set()
for imp in imported_files:
    if imp in all_files_no_ext:
        matched_imports.add(all_files_no_ext[imp])
        
orphans = all_files - matched_imports
for o in sorted(list(orphans))[:20]:
    print(o)
