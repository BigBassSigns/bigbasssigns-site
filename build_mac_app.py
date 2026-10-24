#!/usr/bin/env python3
"""Build the self-contained sRGB Normalize Mac app.

py2app only runs on a Mac. This assembles a minimal .app on any system:
a shell launcher, both Apple silicon and Intel CPython, and Pillow.
The finished app is sRGB Normalize.app in this directory.

    python build_mac_app.py
"""

from __future__ import annotations

import hashlib
import io
import plistlib
import shutil
import struct
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
APP = ROOT / "sRGB Normalize.app"
CACHE = Path("/tmp/normalize-mac-cache")

RELEASE = "20261021"
PYTHON = "3.12.15"
PYTHONS = {
    "arm64": {
        "cpu": 0x0100000C,
        "url": (
            "https://github.com/astral-sh/python-build-standalone/releases/download/"
            f"{RELEASE}/cpython-{PYTHON}%2B{RELEASE}-aarch64-apple-darwin-install_only_stripped.tar.gz"
        ),
        "sha256": "7b8d00b751db21cea87dc551a8f8165147c5fbc5251d5537d7e5497dde00a219",
    },
    "x86_64": {
        "cpu": 0x01000007,
        "url": (
            "https://github.com/astral-sh/python-build-standalone/releases/download/"
            f"{RELEASE}/cpython-{PYTHON}%2B{RELEASE}-x86_64-apple-darwin-install_only_stripped.tar.gz"
        ),
        "sha256": "f12e0504397683d6be0745ffd4c39ef45a455cec169adf35c628840d06133773",
    },
}
WHEELS = {
    "arm64": {
        "cpu": 0x0100000C,
        "url": (
            "https://files.pythonhosted.org/packages/39/4b/"
            "f2ed53d83aa44ac19599ac0a54897f867fafb95f406980d1e24083f8cbe3/"
            "pillow-13.0.0-cp312-cp312-macosx_11_0_arm64.whl"
        ),
        "sha256": "fc481f742ccda20e9ed760b8f978dff50f2a4e9bc253ac167fb0a05b0783ef52",
    },
    "x86_64": {
        "cpu": 0x01000007,
        "url": (
            "https://files.pythonhosted.org/packages/7a/b8/"
            "58d79332229482eb0d27c82973850808c19d37e5bdc14443d3417bd373f5/"
            "pillow-13.0.0-cp312-cp312-macosx_10_13_x86_64.whl"
        ),
        "sha256": "67c8d44ad89fa7eb88de5d6ef6199b1e03dd24974f85a67639fc8badb801fe79",
    },
}

# Runtime does not need headers, Tk, pip, or the IDE.
REMOVE = (
    "include",
    "lib/itcl4.3.8",
    "lib/pkgconfig",
    "lib/tcl9",
    "lib/tcl9.0",
    "lib/thread3.0.6",
    "lib/tk9.0",
    "lib/libtcl9.0.dylib",
    "lib/libtcl9tk9.0.dylib",
    "lib/python3.12/tkinter",
    "lib/python3.12/idlelib",
    "lib/python3.12/turtledemo",
    "lib/python3.12/lib2to3",
    "lib/python3.12/ensurepip",
    "lib/python3.12/config-3.12-darwin",
    "lib/python3.12/lib-dynload/_tkinter.cpython-312-darwin.so",
)

LAUNCHER = r"""#!/bin/bash
# macOS 10.15+ still ships bash 3.2, so this stays compatible with it.
set -eo pipefail
MACOS="$(cd "$(dirname "$0")" && pwd)"
RES="$(cd "$MACOS/../Resources" && pwd)"

args=()
for a in "$@"; do
  case "$a" in
    -psn_*) ;;
    *) args+=("$a") ;;
  esac
done

arch="$(uname -m)"
case "$arch" in
  arm64) PY="$RES/python-arm64/bin/python3.12" ;;
  x86_64) PY="$RES/python-x86_64/bin/python3.12" ;;
  *)
    /usr/bin/osascript -e 'display dialog "sRGB Normalize needs an Apple silicon or Intel Mac." buttons {"OK"} default button "OK" with title "sRGB Normalize"'
    exit 1
    ;;
esac

if [[ ! -x "$PY" ]]; then
  /usr/bin/osascript -e 'display dialog "The Python runtime inside sRGB Normalize is missing." buttons {"OK"} default button "OK" with title "sRGB Normalize"'
  exit 1
fi

export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
if [[ ${#args[@]} -gt 0 ]]; then
  exec "$PY" "$RES/app/drop.py" "${args[@]}"
fi
exec "$PY" "$RES/app/drop.py"
"""

LC_RPATH = 0x8000001C
MH_MAGIC_64 = 0xFEEDFACF


def download(url: str, dest: Path, sha256: str) -> None:
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == sha256:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
    if digest != sha256:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"checksum mismatch for {dest.name}: {digest}")
    tmp.replace(dest)


def mach_header(path: Path) -> tuple[int, list[str]]:
    data = path.read_bytes()
    magic, cpu = struct.unpack_from("<II", data, 0)
    if magic != MH_MAGIC_64:
        raise SystemExit(f"{path} is not a 64-bit Mach-O")
    ncmds = struct.unpack_from("<I", data, 16)[0]
    off = 32
    rpaths = []
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", data, off)
        if cmd == LC_RPATH:
            name_off = struct.unpack_from("<I", data, off + 8)[0]
            raw = data[off + name_off : off + cmdsize]
            rpaths.append(raw.split(b"\x00", 1)[0].decode())
        off += cmdsize
    return cpu, rpaths


def slim(prefix: Path) -> None:
    for relative in REMOVE:
        target = prefix / relative
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()
    bindir = prefix / "bin"
    for item in bindir.iterdir():
        if item.name not in {"python", "python3", "python3.12"}:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()
    site = prefix / "lib/python3.12/site-packages"
    for child in site.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def install_wheel(wheel: Path, site: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        for info in archive.infolist():
            parts = Path(info.filename).parts
            if not parts or parts[0] == ".." or info.filename.startswith("/"):
                raise SystemExit(f"unsafe wheel path {info.filename}")
            archive.extract(info, site)


def extract_python(archive: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    staging = dest.parent / f".extract-{dest.name}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with tarfile.open(archive) as tar:
        tar.extractall(staging, filter="data")
    extracted = staging / "python"
    extracted.rename(dest)
    staging.rmdir()
    python3 = dest / "bin/python3"
    if not python3.is_symlink():
        python3.symlink_to("python3.12")
    python = dest / "bin/python"
    if not python.exists():
        python.symlink_to("python3.12")


def draw_icon(size: int = 1024) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = int(size * 0.04)
    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=int(size * 0.22),
        fill=(28, 28, 28, 255),
    )
    center = size / 2
    radius = size * 0.27
    width = max(2, int(size * 0.055))
    box = [center - radius, center - radius, center + radius, center + radius]
    draw.ellipse(box, outline=(196, 160, 70, 255), width=width)
    dot = size * 0.075
    dx = center + radius * 0.45
    dy = center - radius * 0.82
    draw.ellipse([dx, dy, dx + dot * 2, dy + dot * 2], fill=(186, 42, 36, 255))
    return image


def write_icns(dest: Path) -> None:
    master = draw_icon(1024)
    # type code, pixel size
    sizes = {
        b"icp4": 16,
        b"icp5": 32,
        b"icp6": 64,
        b"ic07": 128,
        b"ic08": 256,
        b"ic09": 512,
        b"ic10": 1024,
        b"ic11": 32,
        b"ic12": 64,
        b"ic13": 256,
        b"ic14": 512,
    }
    chunks = []
    for code, pixels in sizes.items():
        frame = master.resize((pixels, pixels), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        frame.save(buffer, format="PNG")
        png = buffer.getvalue()
        chunks.append(code + struct.pack(">I", 8 + len(png)) + png)
    body = b"".join(chunks)
    dest.write_bytes(b"icns" + struct.pack(">I", 8 + len(body)) + body)


def write_plist(dest: Path) -> None:
    plist = {
        "CFBundleName": "sRGB Normalize",
        "CFBundleDisplayName": "sRGB Normalize",
        "CFBundleIdentifier": "com.bigbasssigns.srgb-normalize",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundlePackageType": "APPL",
        "CFBundleSignature": "????",
        "CFBundleExecutable": "normalize",
        "CFBundleIconFile": "icon",
        "CFBundleInfoDictionaryVersion": "6.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSHumanReadableCopyright": "Big Bass Signs",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "PNG and JPEG images",
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["public.png", "public.jpeg"],
                "CFBundleTypeExtensions": ["png", "jpg", "jpeg"],
            },
            {
                "CFBundleTypeName": "Folder",
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["public.folder"],
            },
        ],
    }
    with dest.open("wb") as handle:
        plistlib.dump(plist, handle)


def build() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if APP.exists():
        shutil.rmtree(APP)
    macos = APP / "Contents/MacOS"
    resources = APP / "Contents/Resources"
    app_dir = resources / "app"
    macos.mkdir(parents=True)
    app_dir.mkdir(parents=True)

    for arch, info in PYTHONS.items():
        archive = CACHE / f"cpython-{arch}.tar.gz"
        wheel = CACHE / Path(WHEELS[arch]["url"]).name
        download(info["url"], archive, info["sha256"])
        download(WHEELS[arch]["url"], wheel, WHEELS[arch]["sha256"])
        prefix = resources / f"python-{arch}"
        extract_python(archive, prefix)
        slim(prefix)
        install_wheel(wheel, prefix / "lib/python3.12/site-packages")
        cpu, rpaths = mach_header(prefix / "bin/python3.12")
        if cpu != info["cpu"]:
            raise SystemExit(f"{arch} python has cpu {cpu:#x}")
        if "@executable_path/../lib" not in rpaths:
            raise SystemExit(f"{arch} python rpath is {rpaths}")
        imaging = next((prefix / "lib/python3.12/site-packages/PIL").glob("_imagingcms*.so"))
        pillow_cpu, _ = mach_header(imaging)
        if pillow_cpu != info["cpu"]:
            raise SystemExit(f"{arch} Pillow has cpu {pillow_cpu:#x}")
        if not (prefix / "lib/libpython3.12.dylib").is_file():
            raise SystemExit(f"{arch} is missing libpython")

    shutil.copy2(ROOT / "normalize.py", app_dir / "normalize.py")
    shutil.copy2(ROOT / "drop.py", app_dir / "drop.py")
    launcher = macos / "normalize"
    launcher.write_text(LAUNCHER)
    launcher.chmod(0o755)
    write_plist(APP / "Contents/Info.plist")
    write_icns(resources / "icon.icns")
    (APP / "Contents/PkgInfo").write_text("APPL????")
    (resources / "VERSION").write_text(
        f"python {PYTHON}+{RELEASE}\npillow 13.0.0\n"
    )
    for arch in PYTHONS:
        binary = resources / f"python-{arch}/bin/python3.12"
        binary.chmod(0o755)


if __name__ == "__main__":
    build()
    print(APP)
