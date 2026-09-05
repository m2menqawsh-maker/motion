import os
import shutil
import glob
import argparse
import re
from pathlib import Path

def sync_templates():
    parser = argparse.ArgumentParser(description="Sync templates and optionally update index")
    parser.add_argument("--source", default="templates", help="Source directory relative to plugin root")
    parser.add_argument("--index", help="Path to the markdown index file to update")
    args = parser.parse_args()

    plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(plugin_root, args.source)
    dest_dir = os.path.join(plugin_root, 'remotion-app', 'src', args.source)
    
    # Clean the destination directory
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    
    # Copy all .tsx and .ts files recursively
    count = 0
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.tsx') or file.endswith('.ts'):
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(root, src_dir)
                dest_sub_dir = os.path.join(dest_dir, rel_path)
                os.makedirs(dest_sub_dir, exist_ok=True)
                shutil.copy(src_file, dest_sub_dir)
                count += 1
                
    print(f"Synced {count} templates to remotion-app/src/{args.source}/")

    if args.index and args.source == "premium-templates":
        index_path = Path(plugin_root) / args.index
        if index_path.exists():
            content = index_path.read_text(encoding="utf-8")
            
            # Simple automatic extraction of components
            lines = ["| File | Exports | Props | Family |", "|---|---|---|---|"]
            for f in sorted(Path(src_dir).rglob("*.tsx")):
                rel_path = f.relative_to(src_dir).as_posix()
                family = rel_path.split('/')[0] if '/' in rel_path else "Unclassified"
                lines.append(f"| `{rel_path}` | — | — | {family.title()} |")
            
            table_md = "\n".join(lines)
            
            if "## 🥇 Premium Templates" in content:
                content = re.sub(
                    r"(## 🥇 Premium Templates.*?\n)(?:.*?)(?=\n## |\Z)", 
                    r"\1" + table_md + "\n", 
                    content, 
                    flags=re.DOTALL
                )
            else:
                insert_pos = content.find("**العدد:")
                if insert_pos == -1: insert_pos = content.find("| File")
                if insert_pos != -1:
                    new_section = "## 🥇 Premium Templates (الأولوية الأولى)\n" + table_md + "\n\n"
                    content = content[:insert_pos] + new_section + content[insert_pos:]
            
            index_path.write_text(content, encoding="utf-8")
            print(f"Updated index at {args.index}")

if __name__ == "__main__":
    sync_templates()
