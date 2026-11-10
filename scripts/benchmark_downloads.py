#!/usr/bin/env python3
"""
Performance benchmark for YouTube Audio Ripper concurrent downloads.

Measures download throughput vs. worker count to help tune DEFAULT_MAX_WORKERS.

Usage:

    python scripts/benchmark_downloads.py --workers 1,2,3,4,5 --url https://youtu.be/dQw4w9WgXcQ

Outputs a markdown table to stdout.
"""

import argparse
import concurrent.futures
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rip_gui import rip_single_url  # noqa: E402


def bench_one(url, output_dir, workers, format="FLAC"):
    """Run a single benchmark: download `workers` copies of `url` concurrently."""
    start = time.perf_counter()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(rip_single_url, url, output_dir, format) for _ in range(workers)]
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())
    elapsed = time.perf_counter() - start

    ok = sum(1 for r in results if r["ok"])
    total_bytes = sum((r["file"].stat().st_size if r["file"] and r["file"].exists() else 0)
                      for r in results if r["ok"])
    return {
        "workers": workers,
        "elapsed_s": round(elapsed, 2),
        "ok": ok,
        "failed": workers - ok,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "mb_per_s": round(total_bytes / (1024 * 1024) / elapsed, 2) if elapsed > 0 else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark concurrent downloads")
    parser.add_argument("--workers", default="1,2,3,4,5",
                        help="Comma-separated worker counts to test (default: 1,2,3,4,5)")
    parser.add_argument("--url", default="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        help="YouTube URL to benchmark against")
    parser.add_argument("--format", default="FLAC", choices=["FLAC", "MP3", "M4A"],
                        help="Output format (default: FLAC)")
    args = parser.parse_args()

    worker_counts = [int(w.strip()) for w in args.workers.split(",") if w.strip()]

    with tempfile.TemporaryDirectory() as td:
        output_dir = Path(td) / "benchmark_output"
        output_dir.mkdir()

        print("# YouTube Audio Ripper — Concurrent Download Benchmark")
        print(f"URL: {args.url}")
        print(f"Format: {args.format}")
        print()

        print("| Workers | Elapsed (s) | OK | Failed | Total (MB) | MB/s |")
        print("|---------|-------------|----|--------|------------|------|")

        for w in worker_counts:
            r = bench_one(args.url, output_dir, w, args.format)
            print(f"| {r['workers']} | {r['elapsed_s']} | {r['ok']} | {r['failed']} | "
                  f"{r['total_mb']} | {r['mb_per_s']} |")

        print()
        print("Note: Results depend on network speed and YouTube throttling.")


if __name__ == "__main__":
    main()
