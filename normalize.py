#!/usr/bin/env python3
"""Prepare a PNG or JPG for VersaWorks.

Converts the image to sRGB, lifts near-black pixels so navy does not crush
to black, and boosts saturation on red-dominant pixels so reds do not go
pink. Writes <name>_sRGB.png next to the original. Run it on the original
again to redo the file; do not run it on the _sRGB output or the lift and
red boost stack a second time.

Requires Pillow.

    python normalize.py art.png photo.jpg
"""

from __future__ import annotations

import array
import io
import sys
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

# Shop prints can be banner-sized. This is a local tool for our own files.
Image.MAX_IMAGE_PIXELS = None

# Every channel under NAVY_MAX is near-black. 1.275 is +27.5%, inside 25–30%.
NAVY_MAX = 40
NAVY_LIFT = 1.275

# Red-dominant means R leads the next channel by at least this many levels.
# Saturation is scaled; hue and brightness stay put.
RED_LEAD = 12
RED_SATURATION = 1.25

_EXTENSIONS = {".png", ".jpg", ".jpeg"}
_SRGB = ImageCms.createProfile("sRGB")
_SRGB_BYTES = ImageCms.ImageCmsProfile(_SRGB).tobytes()


def normalize(path: str | Path) -> Path:
    src = Path(path)
    if src.suffix.lower() not in _EXTENSIONS:
        raise ValueError(f"{src.name} is not a PNG or JPG")
    if not src.is_file():
        raise FileNotFoundError(f"no such file: {src}")

    rgb, alpha, dpi = _load(src)
    rgb = _adjust(rgb)
    if alpha is not None:
        r, g, b = rgb.split()
        rgb = Image.merge("RGBA", (r, g, b, alpha))

    dest = src.with_name(f"{src.stem}_sRGB.png")
    kwargs = {"format": "PNG", "icc_profile": _SRGB_BYTES}
    if dpi:
        kwargs["dpi"] = dpi
    rgb.save(dest, **kwargs)
    return dest


def _load(src: Path):
    with Image.open(src) as im:
        im.load()
        oriented = ImageOps.exif_transpose(im) or im
        dpi = oriented.info.get("dpi")
        icc = oriented.info.get("icc_profile")
        if icc is not None:
            icc = bytes(icc)
        rgb, alpha = _rgb_and_alpha(oriented, icc, src.name)
        rgb.load()
        if alpha is not None:
            alpha.load()
        return rgb.copy(), None if alpha is None else alpha.copy(), dpi


def _rgb_and_alpha(im: Image.Image, icc: bytes | None, name: str):
    if im.mode == "I;16":
        im = _gray16_to_l(im)

    if im.mode in ("P", "PA"):
        keep_alpha = im.mode == "PA" or "transparency" in im.info
        im = im.convert("RGBA" if keep_alpha else "RGB")

    alpha = None
    if im.mode == "RGBA":
        r, g, b, alpha = im.split()
        rgb = _to_srgb(Image.merge("RGB", (r, g, b)), icc, name)
    elif im.mode == "LA":
        gray, alpha = im.split()
        rgb = _to_srgb(gray, icc, name)
    elif im.mode in ("RGB", "L", "CMYK"):
        rgb = _to_srgb(im, icc, name)
    else:
        rgb = im.convert("RGB")

    if rgb.mode != "RGB":
        rgb = rgb.convert("RGB")
    return rgb, alpha


def _to_srgb(im: Image.Image, icc: bytes | None, name: str) -> Image.Image:
    if im.mode == "CMYK" and not icc:
        print(
            f"warning: {name}: CMYK file has no color profile; colors are approximate",
            file=sys.stderr,
        )
    if not icc or _is_srgb(icc):
        return im if im.mode == "RGB" else im.convert("RGB")
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
        print(
            f"warning: {name}: embedded color profile was skipped ({exc})",
            file=sys.stderr,
        )
        return im if im.mode == "RGB" else im.convert("RGB")
    if converted is None or converted.mode != "RGB":
        return im if im.mode == "RGB" else im.convert("RGB")
    return converted


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


def _adjust(im: Image.Image) -> Image.Image:
    """Lift near-black pixels, then protect reds. im is RGB."""

    def tweak(r: int, g: int, b: int):
        if r < NAVY_MAX and g < NAVY_MAX and b < NAVY_MAX:
            r = _byte(r * NAVY_LIFT)
            g = _byte(g * NAVY_LIFT)
            b = _byte(b * NAVY_LIFT)
        second = g if g >= b else b
        if r - second < RED_LEAD:
            return r, g, b
        span_g = r - g
        span_b = r - b
        g2 = r - span_g * RED_SATURATION
        b2 = r - span_b * RED_SATURATION
        if g2 < 0 or b2 < 0:
            span = span_g if span_g >= span_b else span_b
            scale = r / span
            g2 = r - span_g * scale
            b2 = r - span_b * scale
        return r, _byte(g2), _byte(b2)

    src = im.tobytes()
    out = bytearray(len(src))
    for i in range(0, len(src), 3):
        r, g, b = tweak(src[i], src[i + 1], src[i + 2])
        out[i] = r
        out[i + 1] = g
        out[i + 2] = b
    return Image.frombytes("RGB", im.size, bytes(out))


def _byte(value: float) -> int:
    n = int(value + 0.5)
    if n < 0:
        return 0
    if n > 255:
        return 255
    return n


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f"Usage: python {Path(__file__).name} file.png [more.jpg ...]", file=sys.stderr)
        return 1
    failed = False
    for name in argv[1:]:
        try:
            print(normalize(name))
        except Exception as exc:
            print(f"{name}: {exc}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
