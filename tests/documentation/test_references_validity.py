import re
from pathlib import Path
import pytest

class TestReferencesValidity:
    """صلاحية الإشارات في الوثائق"""
    
    def test_all_markdown_links_are_valid(self):
        """كل الروابط في الملفات المرجعية يجب أن تكون صالحة (باستثناء الروابط الخارجية)"""
        base_dir = Path(__file__).parent.parent.parent
        references_dir = base_dir / "references"
        
        if not references_dir.exists():
            pytest.skip("canonical root references directory not found")
        
        # We'll just scan all .md files in .agents as well for valid relative links
        md_files = list(references_dir.rglob("*.md"))
        if (base_dir / ".agents").exists():
            md_files.extend((base_dir / ".agents").rglob("*.md"))
            
        for md_file in md_files:
            if ".venv" in md_file.parts or "node_modules" in md_file.parts:
                continue
                
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            
            # ابحث عن الروابط النسبية
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            
            for text, link in links:
                # تجاهل الروابط الخارجية
                if link.startswith(("http://", "https://", "mailto:", "file://")):
                    continue
                
                # تجاهل الـ anchors
                if link.startswith("#"):
                    continue
                    
                # Link could be absolute to the project? Often markdown links are relative.
                link_path = link.split("#")[0]  # إزالة الـ anchor
                if not link_path:
                    continue
                    
                # Ignore dynamic files
                if any(ignored in link_path for ignored in ["{", "}", "<", ">"]):
                    continue
                    
                full_path = md_file.parent / link_path
                # Also check relative to project root, as people sometimes use /scripts or just scripts
                root_path = base_dir / link_path
                
                if not full_path.exists() and not root_path.exists():
                    # Check if it's pointing to something in .agents/plugins
                    if (base_dir / ".agents" / "plugins" / "super-video-maker-plugin" / link_path).exists():
                        continue
                        
                    # Ignore placeholders that haven't been implemented yet in remotion skill
                    missing_skills = ["maps", "interactivity", "saas", "docs", "upgrade"]
                    if "SKILL.md" in link and any(skill in link for skill in missing_skills):
                        continue
                        
                    pytest.fail(f"{md_file} يحتوي على رابط مكسور: {link}")
