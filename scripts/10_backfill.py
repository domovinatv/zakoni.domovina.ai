"""Backfill orkestrator: vrti pipeline godinu po godinu, od novijih prema starijima.

Za svaku godinu redom pokrece: 01_enumerate -> 02_fetch_rdf -> 03_fetch_html ->
04_parse -> 06_stats. Godina je gotova tek kad 06_stats prodje (exit 0); na gresku
staje i ispisuje dijagnostiku. Sve faze su idempotentne — ponovno pokretanje
preskace preuzeto (raw cache) i obradjeno (anti-join po statusu).

FTS (05) se NE gradi po godini nego jednom na kraju (drop+recreate je skup).

Primjeri:
  uv run python scripts/10_backfill.py --od 2025 --do 2020
  uv run python scripts/10_backfill.py --samo-godina 2019
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAZE = ["01_enumerate.py", "02_fetch_rdf.py", "03_fetch_html.py", "04_parse.py", "06_stats.py"]


def run_faza(script: str, godina: int) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / script), "--godina", str(godina)]
    print(f"\n=== {godina}: {script} ===", flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--od", type=int, default=2025)
    ap.add_argument("--do", type=int, default=1990)
    ap.add_argument("--samo-godina", type=int, default=None)
    args = ap.parse_args()

    godine = [args.samo_godina] if args.samo_godina else list(range(args.od, args.do - 1, -1))
    for g in godine:
        t0 = time.monotonic()
        for script in FAZE:
            rc = run_faza(script, g)
            if rc != 0:
                print(f"\nSTOP: {script} za {g}. pao (exit {rc}). "
                      f"Popravi uzrok pa ponovi: uv run python scripts/10_backfill.py --samo-godina {g}",
                      flush=True)
                sys.exit(rc)
        print(f"\n✓ Godina {g} gotova za {(time.monotonic() - t0) / 60:.1f} min", flush=True)

    print("\nSve godine gotove. Osvjezi FTS i export:")
    print("  uv run python scripts/05_build_fts.py && uv run python scripts/07_export_static.py")


if __name__ == "__main__":
    main()
