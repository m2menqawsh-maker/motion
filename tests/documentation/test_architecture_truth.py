import re
from pathlib import Path
import pytest

class TestArchitectureTruth:
    """حقيقة المعمارية في الوثائق"""
    
    def test_system_architecture_mentions_pipeline_service(self):
        """SYSTEM_ARCHITECTURE.md يجب أن يذكر PipelineService أو scripts/pipeline.py"""
        base_dir = Path(__file__).parent.parent.parent
        arch_file = base_dir / "documentation" / "architecture" / "SYSTEM_ARCHITECTURE.md"
        if arch_file.exists():
            content = arch_file.read_text(encoding="utf-8")
            assert "PipelineService" in content or "pipeline_service" in content or "scripts/pipeline.py" in content, "SYSTEM_ARCHITECTURE.md يجب أن يذكر النظام الجديد"
    
    def test_no_active_docs_mention_scripts_core(self):
        """لا وثيقة نشطة يجب أن تذكر scripts.core بدون تحذير"""
        base_dir = Path(__file__).parent.parent.parent
        doc_files = []
        if (base_dir / "documentation").exists():
            doc_files.extend((base_dir / "documentation").rglob("*.md"))
        if (base_dir / ".agents").exists():
            doc_files.extend((base_dir / ".agents").rglob("*.md"))
            
        for doc_file in doc_files:
            # تجاهل الوثائق المؤرشفة
            if "archive" in str(doc_file).lower() or "quarantine" in str(doc_file).lower():
                continue
            
            try:
                content = doc_file.read_text(encoding="utf-8")
            except Exception:
                continue
            
            # ابحث عن إشارات إلى الأنظمة القديمة
            patterns = ["scripts.core.pipeline", "scripts/core/pipeline", "UnifiedPipeline"]
            for pattern in patterns:
                if pattern in content:
                    # تأكد أنها في سياق تحذيري
                    warning_words = ["deprecated", "forbidden", "prohibited", "archived", "quarantined", "لا", "replaced"]
                    has_warning = any(word in content.lower() for word in warning_words)
                    assert has_warning, f"{doc_file} يذكر {pattern} بدون سياق تحذيري واضح!"
    
    def test_dec_uni_01_is_referenced(self):
        """القرار المعماري DEC-UNI-01 يجب أن يُشار إليه في هيكلية النظام"""
        base_dir = Path(__file__).parent.parent.parent
        arch_file = base_dir / "documentation" / "architecture" / "SYSTEM_ARCHITECTURE.md"
        if arch_file.exists():
            content = arch_file.read_text(encoding="utf-8")
            # We want to make sure the unified pipeline decision is respected
            assert "DEC-UNI-01" in content or "unified pipeline" in content.lower() or "pipeline_state.json" in content
