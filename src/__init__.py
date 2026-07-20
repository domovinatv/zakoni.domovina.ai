"""Podaci (data/, frontend/public/data) zive na vanjskom disku i symlinkani su
u repo — prije bilo kakvog rada provjeri da je disk montiran, inace bi skripte
pale s nejasnim PermissionError pokusavajuci pisati u /Volumes.
"""

import pathlib

_ROOT = pathlib.Path(__file__).resolve().parent.parent

for _p in (_ROOT / "data", _ROOT / "frontend" / "public" / "data"):
    if _p.is_symlink() and not _p.exists():
        raise RuntimeError(
            f"{_p} pokazuje na {_p.readlink()} koji nije dostupan — "
            "montiraj vanjski disk DOMOVINA2TB pa pokusaj ponovo."
        )
