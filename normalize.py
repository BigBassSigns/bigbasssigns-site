#!/usr/bin/env python3
"""Convert a PNG or JPG to sRGB and print a short color diagnostic.

Writes <name>_sRGB.png next to the original. Pixel values are not lifted
or recolored. The diagnostic reports the profile, size, and how many
pixels are near-black or red-dominant. Folders are scanned for PNG and
JPG files. Files that already end in _sRGB are left alone.

Requires Pillow.

    python normalize.py art.png photo.jpg folder/
"""

from __future__ import annotations

import array
import io
import sys
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

# Shop prints can be banner-sized. This is a local tool for our own files.
Image.MAX_IMAGE_PIXELS = None

# Reported only. These pixels are not changed.
NEAR_BLACK = 40
RED_LEAD = 12

_EXTENSIONS = {".png", ".jpg", ".jpeg"}
_SRGB = ImageCms.createProfile("sRGB")
_SRGB_BYTES = ImageCms.ImageCmsProfile(_SRGB).tobytes()


def collect_inputs(items) -> tuple[list[Path], list[str], list[str]]:
    """Return PNG/JPG files, error messages, and skip notes.

    A folder contributes the images inside it, including nested folders.
    Hidden files are ignored. An explicit file that is not a PNG or JPG is
    an error. Outputs from an earlier run are skipped.
    """
    files: list[Path] = []
    errors: list[str] = []
    notes: list[str] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path)
        if key not in seen:
            seen.add(key)
            files.append(path)

    for raw in items:
        path = Path(raw).expanduser()
        if not path.exists():
            errors.append(f"no such file: {path}")
            continue
        if path.is_dir():
            for found in path.rglob("*"):
                if not found.is_file():
                    continue
                relative = found.relative_to(path)
                if any(part.startswith(".") for part in relative.parts):
                    continue
                if found.suffix.lower() not in _EXTENSIONS:
                    continue
                if found.stem.endswith("_sRGB"):
                    continue
                add(found)
            continue
        if path.suffix.lower() not in _EXTENSIONS:
            errors.append(f"{path.name} is not a PNG or JPG")
            continue
        if path.stem.endswith("_sRGB"):
            notes.append(f"skipped {path.name} (already normalized)")
            continue
        add(path)

    files.sort(key=lambda item: str(item).lower())
    return files, errors, notes


def normalize(path: str | Path) -> tuple[Path, str]:
    src = Path(path)
    if src.suffix.lower() not in _EXTENSIONS:
        raise ValueError(f"{src.name} is not a PNG or JPG")
    if not src.is_file():
        raise FileNotFoundError(f"no such file: {src}")

    rgb, alpha, dpi, note = _load(src)
    diagnostic = _diagnostic(src.name, rgb, alpha is not None, dpi, note)
    if alpha is not None:
        r, g, b = rgb.split()
        rgb = Image.merge("RGBA", (r, g, b, alpha))

    dest = src.with_name(f"{src.stem}_sRGB.png")
    kwargs = {"format": "PNG", "icc_profile": _SRGB_BYTES}
    if dpi:
        kwargs["dpi"] = dpi
    rgb.save(dest, **kwargs)
    return dest, diagnostic


def _load(src: Path):
    with Image.open(src) as im:
        im.load()
        oriented = ImageOps.exif_transpose(im) or im
        dpi = oriented.info.get("dpi")
        icc = oriented.info.get("icc_profile")
        if icc is not None:
            icc = bytes(icc)
        rgb, alpha, note = _rgb_and_alpha(oriented, icc)
        rgb.load()
        if alpha is not None:
            alpha.load()
        return rgb.copy(), None if alpha is None else alpha.copy(), dpi, note


def _rgb_and_alpha(im: Image.Image, icc: bytes | None):
    if im.mode == "I;16":
        im = _gray16_to_l(im)

    if im.mode in ("P", "PA"):
        keep_alpha = im.mode == "PA" or "transparency" in im.info
        im = im.convert("RGBA" if keep_alpha else "RGB")

    alpha = None
    if im.mode == "RGBA":
        r, g, b, alpha = im.split()
        rgb, note = _to_srgb(Image.merge("RGB", (r, g, b)), icc)
    elif im.mode == "LA":
        gray, alpha = im.split()
        rgb, note = _to_srgb(gray, icc)
    elif im.mode in ("RGB", "L", "CMYK"):
        rgb, note = _to_srgb(im, icc)
    else:
        rgb, note = im.convert("RGB"), "converted to RGB"

    if rgb.mode != "RGB":
        rgb = rgb.convert("RGB")
    return rgb, alpha, note


def _to_srgb(im: Image.Image, icc: bytes | None) -> tuple[Image.Image, str]:
    if im.mode == "CMYK" and not icc:
        rgb = im.convert("RGB")
        return rgb, "CMYK with no profile; colors are approximate"
    if not icc:
        rgb = im if im.mode == "RGB" else im.convert("RGB")
        return rgb, "no profile, treated as sRGB"
    if _is_srgb(icc):
        rgb = im if im.mode == "RGB" else im.convert("RGB")
        return rgb, "already sRGB"
    try:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        converted = ImageCms.profileToProfile(
            im,
            src,
            _SRGB,
            renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
            outputMode="RGB",
            flags=ImageCms.Flags.BLACKPOINTCOMPENSATION,
        )
    except Exception as exc:
        rgb = im if im.mode == "RGB" else im.convert("RGB")
        return rgb, f"profile skipped ({exc})"
    if converted is None or converted.mode != "RGB":
        rgb = im if im.mode == "RGB" else im.convert("RGB")
        return rgb, "profile skipped"
    return converted, f"{_profile_name(icc)} converted to sRGB"


def _is_srgb(icc: bytes) -> bool:
    try:
        desc = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc)))
    except Exception:
        return False
    if isinstance(desc, bytes):
        text = desc.decode("latin-1", "replace")
    else:
        text = str(desc)
    return "srgb" in "".join(text.lower().split())


def _gray16_to_l(im: Image.Image) -> Image.Image:
    values = array.array("H")
    values.frombytes(im.tobytes())
    out = array.array("B", ((v * 255 + 32767) // 65535 for v in values))
    return Image.frombytes("L", im.size, out.tobytes())


def _profile_name(icc: bytes) -> str:
    try:
        desc = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc)))
    except Exception:
        return "embedded profile"
    if isinstance(desc, bytes):
        text = desc.decode("latin-1", "replace")
    else:
        text = str(desc)
    text = " ".join(text.split())
    return text or "embedded profile"


def _diagnostic(name: str, rgb: Image.Image, has_alpha: bool, dpi, note: str) -> str:
    width, height = rgb.size
    mode = "RGBA" if has_alpha else "RGB"
    raw = rgb.tobytes()
    total = len(raw) // 3
    near = red = 0
    for i in range(0, len(raw), 3):
        r = raw[i]
        g = raw[i + 1]
        b = raw[i + 2]
        if r < NEAR_BLACK and g < NEAR_BLACK and b < NEAR_BLACK and (r or g or b):
            near += 1
        second = g if g >= b else b
        if r - second >= RED_LEAD:
            red += 1
    parts = [f"{name}: {width}×{height} {mode}"]
    if dpi:
        parts.append(f"{_dpi(dpi)} dpi")
    parts.append(note)
    if total:
        if near:
            parts.append(f"near-black {near} px ({_pct(near, total)})")
        if red:
            parts.append(f"red-dominant {red} px ({_pct(red, total)})")
        if not near and not red:
            parts.append("no near-black or red-dominant pixels")
    return " — ".join(parts)


def _dpi(dpi) -> str:
    try:
        x, y = dpi
    except (TypeError, ValueError):
        return str(dpi)
    if abs(x - y) < 0.5:
        return str(int(round(x)))
    return f"{x:.0f}×{y:.0f}"


def _pct(count: int, total: int) -> str:
    return f"{count / total * 100:.1f}%"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            f"Usage: python {Path(__file__).name} file.png [more.jpg folder ...]",
            file=sys.stderr,
        )
        return 1
    files, errors, notes = collect_inputs(argv[1:])
    for note in notes:
        print(note, file=sys.stderr)
    for error in errors:
        print(error, file=sys.stderr)
    if not files:
        if not errors and not notes:
            print("No PNG or JPG files found.", file=sys.stderr)
        return 1 if errors or not notes else 0
    failed = bool(errors)
    for path in files:
        try:
            dest, diagnostic = normalize(path)
            print(diagnostic)
            print(dest)
        except Exception as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
