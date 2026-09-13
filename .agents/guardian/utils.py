#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import time
import datetime
import logging
from pathlib import Path
from functools import lru_cache
try:
    from jsonschema import validate, ValidationError
except ImportError:
    validate = None

LOG_FILE = Path(".agents/logs/guardrails.log")
CIRCUIT_BREAKER_FILE = Path(".agents/guardian/circuit_breaker.json")

logger = logging.getLogger("Guardian")

def get_default_config() -> dict:
    return {
        "command_violations": [],
        "behavioral_violations": [],
        "protocol_violations": [],
        "plan_quality_violations": [],
        "write_violations": {
            "blocked_paths": [],
            "blocked_files": [],
            "allowed_prefixes": ["projects/", "scratch/", "assets/incoming/", ".agents/logs/"]
        },
        "command_restrictions": {
            "blocked_commands": [],
            "destructive_patterns": [],
            "protected_from_destruction": [],
            "allowed_packages": []
        },
        "post_execution_warnings": {}
    }

@lru_cache(maxsize=1)
def load_config() -> dict:
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "config" / "violations_config.json"
    schema_path = base_dir / "config" / "violations_config.schema.json"
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        if validate and schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as sf:
                schema = json.load(sf)
            try:
                validate(instance=config, schema=schema)
            except ValidationError as e:
                logger.error(f"Schema validation failed: {e}")
                return get_default_config()
                
        return config
    except FileNotFoundError:
        logger.error("violations_config.json not found, using defaults")
        return get_default_config()
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in violations_config.json: {e}")
        return get_default_config()

def log_audit(decision: str, reason: str, context: str, prefix: str = "GUARD"):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{prefix}] [{decision}] CONTEXT: {context} | REASON: {reason}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass

def check_circuit_breaker(tool_name: str, command: str) -> str:
    """Returns an error message if the circuit breaker is tripped, otherwise empty string."""
    if not CIRCUIT_BREAKER_FILE.exists():
        return ""
        
    lock_dir = CIRCUIT_BREAKER_FILE.with_suffix(".lock")
    for _ in range(50):
        try:
            lock_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            time.sleep(0.1)
    else:
        pass
        
    try:
        with open(CIRCUIT_BREAKER_FILE, "r", encoding="utf-8") as f:
            cb_data = json.load(f)
            
        sig = str(command)[:50] if command else "default"
        key = f"{tool_name}::{sig}"
        
        if key in cb_data:
            failures = cb_data[key].get("failures", 0)
            last_fail = cb_data[key].get("last_failure_timestamp", 0)
            now = time.time()
            if now - last_fail > 900:
                failures = 0
            if failures >= 3:
                return f"🛑 CIRCUIT BREAKER TRIPPED: Tool failed 3 times. Stop and ask the user for manual intervention."
    except Exception:
        pass
    finally:
        try:
            lock_dir.rmdir()
        except Exception:
            pass
            
    return ""

def update_circuit_breaker(tool_name: str, command: str, exit_code: int):
    lock_dir = CIRCUIT_BREAKER_FILE.with_suffix(".lock")
    for _ in range(50):
        try:
            lock_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            time.sleep(0.1)
    else:
        pass
        
    try:
        cb_data = {}
        if CIRCUIT_BREAKER_FILE.exists():
            try:
                with open(CIRCUIT_BREAKER_FILE, "r", encoding="utf-8") as f:
                    cb_data = json.load(f)
            except Exception:
                pass
                
        sig = str(command)[:50] if command else "default"
        key = f"{tool_name}::{sig}"
        
        now = time.time()
        if key not in cb_data:
            cb_data[key] = {"failures": 0, "last_failure_timestamp": 0.0}
            
        if now - cb_data[key].get("last_failure_timestamp", 0) > 900:
            cb_data[key]["failures"] = 0
            
        if exit_code != 0:
            cb_data[key]["failures"] += 1
            cb_data[key]["last_failure_timestamp"] = now
        else:
            cb_data[key]["failures"] = 0
            
        CIRCUIT_BREAKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CIRCUIT_BREAKER_FILE, "w", encoding="utf-8") as f:
            json.dump(cb_data, f, ensure_ascii=False, indent=2)
            
    finally:
        try:
            lock_dir.rmdir()
        except Exception:
            pass

def is_path_safe(file_path: str, allowed_prefixes: list) -> bool:
    # Normalize Windows slashes
    file_path = file_path.replace("\\", "/")
    
    # Absolute paths are blocked
    if Path(file_path).is_absolute() or file_path.startswith("/") or file_path[1:3] == ":/":
        return False
        
    # Parent directory traversal is blocked
    if ".." in file_path:
        return False
        
    # Must start with allowed prefix
    return any(file_path.startswith(prefix) for prefix in allowed_prefixes)
