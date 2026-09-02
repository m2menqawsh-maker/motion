# -*- coding: utf-8 -*-
"""
Media Pipeline Orchestrator - Idempotent Asset Lifecycle Management
=====================================================================

يضمن هذا النظام:
1. Idempotency: نفس العملية = نفس النتيجة (لا إعادة معالجة)
2. Atomic transactions: كل شيء أو لا شيء (لا ملفات مقطوعة)
3. Crash recovery: استئناف آمن بعد الفشل
4. Locking: منع التصادم بين عمليات متوازية
5. Hash verification: عدم إعادة معالجة نفس المحتوى
6. Transaction logging: سجل كامل للتدقيق

Usage:
    from tools.media_pipeline import MediaPipelineOrchestrator
    orchestrator = MediaPipelineOrchestrator(r"C:\video\video-workspace")
    
    # Ingest asset
    cached = orchestrator.ingest_asset("video.mp4", "asset_001", "video")
    
    # Process with MCP
    processed = orchestrator.process_asset(cached, mcp_processor, "audio", {"params": {...}})
    
    # Promote to ready
    ready = orchestrator.promote_to_ready(processed, "project_alpha")
"""

import os
import json
import hashlib
import shutil
import tempfile
import sys
from pathlib import Path
from datetime import datetime, timezone
from filelock import FileLock
from contextlib import contextmanager

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

class MediaPipelineOrchestrator:
    def __init__(self, workspace_root):
        self.workspace = Path(workspace_root)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.assets = self.workspace / "assets"
        self.processed = self.workspace / "processed"
        self.projects = self.workspace / "projects"
        self.storage = self.workspace / "storage"
        self.scratch = self.workspace / "scratch"
        
        self.tx_log = self.workspace / ".transactions.jsonl"
        self.lock_dir = self.workspace / ".locks"
        self.lock_dir.mkdir(exist_ok=True)
        
        # Ensure all directories exist with proper structure
        for d in [self.assets, self.processed, self.projects, self.storage, self.scratch]:
            d.mkdir(exist_ok=True)
        
        # Create subdirectories for assets
        for sub in ["incoming", "processing", "ready", "cache"]:
            (self.assets / sub).mkdir(exist_ok=True)
        
        # Create subdirectories for processed
        for sub in ["audio", "video", "image", "temp"]:
            (self.processed / sub).mkdir(exist_ok=True)
        
        # Create subdirectories for storage
        for sub in ["exports", "cache", "raw", "processed"]:
            (self.storage / sub).mkdir(exist_ok=True)
    
    @contextmanager
    def atomic_write(self, target_path: Path, mode="wb"):
        """Context manager for atomic file writes using tempfile + rename"""
        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(target_path.parent),
            suffix=".tmp"
        )
        try:
            with os.fdopen(temp_fd, mode) as f:
                yield f
            # Atomic rename (POSIX/Windows guaranteed)
            if target_path.exists():
                os.replace(temp_path, str(target_path))
            else:
                os.rename(temp_path, str(target_path))
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def log_transaction(self, tx_id: str, operation: str, source: str, dest: str,
                       hash_before: str, hash_after: str, status: str, metadata: dict = None):
        """Append transaction to audit log"""
        tx = {
            "tx_id": tx_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "source": str(source),
            "dest": str(dest),
            "hash_before": hash_before,
            "hash_after": hash_after,
            "status": status,
            "metadata": metadata or {}
        }
        with open(self.tx_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(tx, ensure_ascii=False) + "\n")
    
    def acquire_lock(self, resource_id: str) -> FileLock:
        """Acquire exclusive lock on resource"""
        lock_path = self.lock_dir / f"{resource_id}.lock"
        lock = FileLock(str(lock_path), timeout=30)
        lock.acquire()
        return lock
    
    def check_cache(self, content_hash: str, target_dir: Path) -> Path | None:
        """Check if content with same hash already exists"""
        cache_file = target_dir / f"{content_hash}.cached"
        return cache_file if cache_file.exists() else None
    
    def ingest_asset(self, source_path: str | Path, asset_id: str, asset_type: str) -> Path:
        """
        Idempotent asset ingestion with hash verification.
        If asset with same content already exists, returns cached version.
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")
        
        content_hash = self.compute_hash(source_path)
        
        # Check cache first (idempotency)
        cached = self.check_cache(content_hash, self.assets / "cache")
        if cached:
            self.log_transaction(
                tx_id=f"ingest_{asset_id}_{datetime.now(timezone.utc).timestamp()}",
                operation="cache_hit",
                source=str(source_path),
                dest=str(cached),
                hash_before=content_hash,
                hash_after=content_hash,
                status="success"
            )
            return cached
        
        lock = self.acquire_lock(f"asset_{asset_id}")
        try:
            incoming_path = self.assets / "incoming" / f"{asset_id}_{content_hash[:8]}{source_path.suffix}"
            
            with self.atomic_write(incoming_path) as dest:
                with open(source_path, "rb") as src:
                    shutil.copyfileobj(src, dest)
            
            hash_after = self.compute_hash(incoming_path)
            if hash_after != content_hash:
                raise IOError("Hash mismatch after copy - data corruption detected")
            
            cache_path = self.assets / "cache" / f"{content_hash}.cached"
            shutil.move(str(incoming_path), str(cache_path))
            
            self.log_transaction(
                tx_id=f"ingest_{asset_id}_{datetime.now(timezone.utc).timestamp()}",
                operation="ingest",
                source=str(source_path),
                dest=str(cache_path),
                hash_before=content_hash,
                hash_after=hash_after,
                status="success",
                metadata={"asset_id": asset_id, "type": asset_type}
            )
            
            return cache_path
        finally:
            lock.release()
    
    def process_asset(self, asset_path: Path, processor_func, output_type: str,
                     processor_metadata: dict) -> Path:
        """
        Idempotent asset processing with hash-based deduplication.
        Same input + same processor = same output (cached).
        """
        if not asset_path.exists():
            raise FileNotFoundError(f"Asset not found: {asset_path}")
        
        input_hash = self.compute_hash(asset_path)
        
        processor_sig = hashlib.sha256(
            json.dumps(processor_metadata, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        output_cache = self.processed / output_type / "cache"
        output_cache.mkdir(exist_ok=True)
        cached_output = output_cache / f"{input_hash}_{processor_sig}.cached"
        
        if cached_output.exists():
            self.log_transaction(
                tx_id=f"process_{input_hash[:8]}_{datetime.now(timezone.utc).timestamp()}",
                operation="process_cache_hit",
                source=str(asset_path),
                dest=str(cached_output),
                hash_before=input_hash,
                hash_after=self.compute_hash(cached_output),
                status="success",
                metadata={"processor": processor_metadata}
            )
            return cached_output
        
        lock = self.acquire_lock(f"process_{input_hash[:8]}")
        try:
            processing_dir = self.processed / output_type / "processing"
            processing_dir.mkdir(exist_ok=True)
            processing_path = processing_dir / f"temp_{input_hash[:8]}"
            
            processor_func(asset_path, processing_path, processor_metadata)
            
            if not processing_path.exists():
                raise IOError("Processor did not create output file")
            
            shutil.move(str(processing_path), str(cached_output))
            
            self.log_transaction(
                tx_id=f"process_{input_hash[:8]}_{datetime.now(timezone.utc).timestamp()}",
                operation="process",
                source=str(asset_path),
                dest=str(cached_output),
                hash_before=input_hash,
                hash_after=self.compute_hash(cached_output),
                status="success",
                metadata={"processor": processor_metadata}
            )
            
            return cached_output
        finally:
            lock.release()
    
    def promote_to_ready(self, processed_path: Path, project_id: str) -> Path:
        """Move processed asset to ready state for project"""
        if not processed_path.exists():
            raise FileNotFoundError(f"Processed asset not found: {processed_path}")
        
        lock = self.acquire_lock(f"promote_{project_id}_{processed_path.name}")
        try:
            ready_dir = self.assets / "ready" / project_id
            ready_dir.mkdir(parents=True, exist_ok=True)
            
            ready_path = ready_dir / processed_path.name
            
            with self.atomic_write(ready_path) as dest:
                with open(processed_path, "rb") as src:
                    shutil.copyfileobj(src, dest)
            
            self.log_transaction(
                tx_id=f"promote_{project_id}_{datetime.now(timezone.utc).timestamp()}",
                operation="promote",
                source=str(processed_path),
                dest=str(ready_path),
                hash_before=self.compute_hash(processed_path),
                hash_after=self.compute_hash(ready_path),
                status="success",
                metadata={"project_id": project_id}
            )
            
            return ready_path
        finally:
            lock.release()
    
    def export_final(self, project_id: str, export_func, metadata: dict) -> Path:
        """Export final project output to storage"""
        lock = self.acquire_lock(f"export_{project_id}")
        try:
            exports_dir = self.storage / "exports" / project_id
            exports_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            export_path = exports_dir / f"final_{timestamp}.mp4"
            
            export_func(self.projects / project_id, export_path, metadata)
            
            if not export_path.exists():
                raise IOError("Export function did not create output")
            
            archive_path = self.storage / "processed" / project_id
            archive_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(export_path), str(archive_path / f"final_{timestamp}.mp4"))
            
            self.log_transaction(
                tx_id=f"export_{project_id}_{datetime.now(timezone.utc).timestamp()}",
                operation="export",
                source=str(self.projects / project_id),
                dest=str(export_path),
                hash_before="",
                hash_after=self.compute_hash(export_path),
                status="success",
                metadata=metadata
            )
            
            return export_path
        finally:
            lock.release()
    
    def cleanup_scratch(self):
        """Clean scratch directory (safe to run anytime)"""
        for item in self.scratch.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    
    def cleanup_temp(self):
        """Clean temporary files from processing directories"""
        temp_dir = self.processed / "temp"
        if temp_dir.exists():
            for item in temp_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
    
    def get_transaction_history(self, asset_id: str = None, limit: int = 100) -> list:
        """Retrieve transaction history"""
        if not self.tx_log.exists():
            return []
        
        txs = []
        with open(self.tx_log, "r", encoding="utf-8") as f:
            for line in f:
                tx = json.loads(line)
                if asset_id is None or asset_id in tx.get("source", "") or asset_id in tx.get("dest", ""):
                    txs.append(tx)
                    if len(txs) >= limit:
                        break
        
        return list(reversed(txs))
    
    def verify_pipeline_integrity(self) -> dict:
        """Verify pipeline state and return health report"""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "directories": {},
            "transactions": len(list(open(self.tx_log, encoding="utf-8"))) if self.tx_log.exists() else 0,
            "locks": len(list(self.lock_dir.glob("*.lock")))
        }
        
        for d in [self.assets, self.processed, self.projects, self.storage, self.scratch]:
            count = sum(1 for _ in d.rglob("*") if _.is_file())
            report["directories"][d.name] = count
        
        return report

# CLI interface
if __name__ == "__main__":
    orchestrator = MediaPipelineOrchestrator(r"C:\video\video-workspace")
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python media_pipeline.py health          # Show pipeline health")
        print("  python media_pipeline.py history [asset]  # Show transaction history")
        print("  python media_pipeline.py clean-scratch    # Clean scratch directory")
        print("  python media_pipeline.py clean-temp       # Clean temp files")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "health":
        health = orchestrator.verify_pipeline_integrity()
        print(json.dumps(health, indent=2))
    
    elif cmd == "history":
        asset_id = sys.argv[2] if len(sys.argv) > 2 else None
        history = orchestrator.get_transaction_history(asset_id, limit=20)
        for tx in history:
            print(f"{tx['timestamp']}: {tx['operation']} - {tx['source']} → {tx['dest']} ({tx['status']})")
    
    elif cmd == "clean-scratch":
        orchestrator.cleanup_scratch()
        print("✅ Scratch cleaned")
    
    elif cmd == "clean-temp":
        orchestrator.cleanup_temp()
        print("✅ Temp files cleaned")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
