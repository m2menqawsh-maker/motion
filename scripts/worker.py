#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical Pipeline Worker Entrypoint for S21.

Usage:
    python scripts/worker.py [--worker-id <id>] [--poll-interval 1.0] [--single-run]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.core.worker import PipelineWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [worker] %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Clean Video Workspace - Pipeline Worker")
    parser.add_argument("--worker-id", type=str, default=None, help="Explicit worker ID")
    parser.add_argument("--db-path", type=str, default=None, help="Custom database path")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--lease-duration", type=float, default=30.0, help="Lease TTL duration in seconds")
    parser.add_argument("--heartbeat-interval", type=float, default=5.0, help="Heartbeat renewal interval")
    parser.add_argument("--single-run", action="store_true", help="Process at most one run and exit")
    parser.add_argument("--max-runs", type=int, default=None, help="Process up to N runs and exit")

    args = parser.parse_args()

    max_runs = 1 if args.single_run else args.max_runs

    worker = PipelineWorker(
        worker_id=args.worker_id,
        db_path=args.db_path,
        poll_interval=args.poll_interval,
        lease_duration=args.lease_duration,
        heartbeat_interval=args.heartbeat_interval,
        max_runs=max_runs,
    )

    worker.run_loop()


if __name__ == "__main__":
    main()
