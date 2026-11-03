"""Lossless I/O helpers for dataset preparation (02/11 scope)."""

import hashlib
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_float_tiff(path, data):
    path = Path(path)
    data = np.asarray(data, dtype=np.float32)
    if data.ndim != 2 or not np.isfinite(data).all():
        raise ValueError("Calibration must be a finite 2D array")
    if path.exists():
        with tifffile.TiffFile(path) as tif:
            previous = tif.asarray()
            valid = (len(tif.pages) == 1 and int(tif.pages[0].compression) == 1
                     and previous.dtype.kind == "f" and previous.dtype.itemsize == 4)
        if valid and np.array_equal(previous, data):
            return
        raise FileExistsError(f"Refusing to replace different calibration: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(path, data, compression=None, photometric="minisblack")
