import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_tree(dir_path, prefix='', exclude=None):
    if exclude is None:
        exclude = set()
    
    path = Path(dir_path)
    if not path.exists():
        return ''
        
    items = sorted([x for x in path.iterdir() if x.name not in exclude], 
                   key=lambda x: (not x.is_dir(), x.name.lower()))
    
    out = ''
    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = '└── ' if is_last else '├── '
        out += f'{prefix}{connector}{item.name}\n'
        
        if item.is_dir():
            new_prefix = prefix + ('    ' if is_last else '│   ')
            out += get_tree(item, new_prefix, exclude)
    return out

exclude_dirs = {'node_modules', '.venv', '.git', '__pycache__', 'dist', 'build', '.remotion', 'out', 'node_modules.bak'}
tree_str = get_tree(r'c:\video\clean-video-workspace\.agents', exclude=exclude_dirs)

agents_md = Path(r'c:\video\clean-video-workspace\.agents\AGENTS.md')
router_md = Path(r'c:\video\clean-video-workspace\.agents\plugins\super-video-maker-plugin\references\ROUTER.md')
vocab_md = Path(r'c:\video\clean-video-workspace\.agents\plugins\super-video-maker-plugin\reference\ground-truth\VOCAB_REMAP.md')
protocol_md = Path(r'c:\video\clean-video-workspace\.agents\rules\video-production-protocol.md')
template_index_md = Path(r'c:\video\clean-video-workspace\.agents\plugins\super-video-maker-plugin\reference\ground-truth\TEMPLATE_INDEX.md')

def read_file(p):
    if p.exists():
        return p.read_text(encoding='utf-8')
    return 'ملف غير موجود'

markdown_content = f"""# نظرة عامة على المشروع (Project Overview)

هذا الملف يحتوي على النظرة العامة الشاملة لبيئة وكيل الموشن التجاري `.agents`، شاملة شجرة الملفات وملفات التوجيه الأساسية.

## 1. شجرة ملفات بيئة العمل (.agents)
> تم استثناء مجلدات المكتبات الكبيرة (مثل `node_modules` و `.venv`).

```text
.agents
{tree_str}
```

## 2. ملفات التوجيه والقواعد الإلزامية

### 2.1 القواعد الأساسية للوكيل (AGENTS.md)
<details>
<summary>اضغط لعرض AGENTS.md</summary>

```markdown
{read_file(agents_md)}
```
</details>

### 2.2 بروتوكول إنتاج الفيديو (video-production-protocol.md)
<details>
<summary>اضغط لعرض video-production-protocol.md</summary>

```markdown
{read_file(protocol_md)}
```
</details>

### 2.3 محرك القرار وراوتر العمليات (ROUTER.md)
<details>
<summary>اضغط لعرض ROUTER.md</summary>

```markdown
{read_file(router_md)}
```
</details>

### 2.4 جدول إعادة التوجيه للأسماء (VOCAB_REMAP.md)
<details>
<summary>اضغط لعرض VOCAB_REMAP.md</summary>

```markdown
{read_file(vocab_md)}
```
</details>

### 2.5 فهرس القوالب الحي (TEMPLATE_INDEX.md)
<details>
<summary>اضغط لعرض TEMPLATE_INDEX.md</summary>

```markdown
{read_file(template_index_md)}
```
</details>
"""

out_path = Path(r'c:\video\clean-video-workspace\project_overview.md')
out_path.write_text(markdown_content, encoding='utf-8')
print(f'Created: {out_path}')
