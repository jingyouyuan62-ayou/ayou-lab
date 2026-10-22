#!/usr/bin/env python3
"""Prepare small vision copies and keep resumable archive work state.

This script intentionally uses only the Python standard library and macOS
``sips``. It never modifies source images or data/entries.json.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "archive-work"
VISION_DIR = WORK_DIR / "vision"
ANALYSIS_DIR = WORK_DIR / "analyses"
PROGRESS_PATH = WORK_DIR / "progress.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
STATUSES = {
    "prepared",
    "analyzing",
    "analysis_saved",
    "imported",
    "skipped",
    "rejected",
}
DUPLICATE_HINT_DISTANCE = 12
PROXY_WARN_BYTES = 2 * 1024 * 1024


def utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def run_sips(*args):
    return subprocess.run(
        ["sips", *map(str, args)],
        check=True,
        capture_output=True,
        text=True,
    )


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path):
    result = run_sips("-g", "pixelWidth", "-g", "pixelHeight", path)
    values = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() in {"pixelWidth", "pixelHeight"}:
            values[key.strip()] = int(value.strip())
    if set(values) != {"pixelWidth", "pixelHeight"}:
        raise RuntimeError("could not read dimensions for {}".format(path))
    return values["pixelWidth"], values["pixelHeight"]


def bmp_pixels(path):
    data = path.read_bytes()
    if data[:2] != b"BM":
        raise RuntimeError("sips did not produce a BMP file")

    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size < 40:
        raise RuntimeError("unsupported BMP header")

    width = struct.unpack_from("<i", data, 18)[0]
    signed_height = struct.unpack_from("<i", data, 22)[0]
    bits_per_pixel = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if width <= 0 or signed_height == 0 or compression not in {0, 3}:
        raise RuntimeError("unsupported BMP layout")
    if bits_per_pixel not in {24, 32}:
        raise RuntimeError("unsupported BMP pixel depth")
    if compression == 3 and bits_per_pixel != 32:
        raise RuntimeError("unsupported bitfield BMP layout")

    height = abs(signed_height)
    top_down = signed_height < 0
    bytes_per_pixel = bits_per_pixel // 8
    stride = ((width * bits_per_pixel + 31) // 32) * 4
    rows = []

    for y in range(height):
        source_y = y if top_down else height - y - 1
        row_start = pixel_offset + source_y * stride
        row = []
        for x in range(width):
            start = row_start + x * bytes_per_pixel
            blue, green, red = data[start : start + 3]
            row.append(round(0.299 * red + 0.587 * green + 0.114 * blue))
        rows.append(row)
    return rows


def bmp_rgb_pixels(path):
    data = path.read_bytes()
    if data[:2] != b"BM":
        raise RuntimeError("sips did not produce a BMP file")

    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size < 40:
        raise RuntimeError("unsupported BMP header")

    width = struct.unpack_from("<i", data, 18)[0]
    signed_height = struct.unpack_from("<i", data, 22)[0]
    bits_per_pixel = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if width <= 0 or signed_height == 0 or compression not in {0, 3}:
        raise RuntimeError("unsupported BMP layout")
    if bits_per_pixel not in {24, 32}:
        raise RuntimeError("unsupported BMP pixel depth")
    if compression == 3 and bits_per_pixel != 32:
        raise RuntimeError("unsupported bitfield BMP layout")

    height = abs(signed_height)
    top_down = signed_height < 0
    bytes_per_pixel = bits_per_pixel // 8
    stride = ((width * bits_per_pixel + 31) // 32) * 4
    rows = []

    for y in range(height):
        source_y = y if top_down else height - y - 1
        row_start = pixel_offset + source_y * stride
        row = []
        for x in range(width):
            start = row_start + x * bytes_per_pixel
            blue, green, red = data[start : start + 3]
            row.append((red, green, blue))
        rows.append(row)
    return rows


def content_bounds(pixels):
    """Trim near-uniform letterboxing before comparing image structure."""
    height = len(pixels)
    width = len(pixels[0])
    top, bottom, left, right = 0, height, 0, width

    def uniform_edge(values):
        ordered = sorted(values)
        median = ordered[len(ordered) // 2]
        close = sum(abs(value - median) <= 18 for value in values)
        return close / len(values) >= 0.9

    while top + 16 < bottom and uniform_edge(pixels[top][left:right]):
        top += 1
    while bottom - top > 16 and uniform_edge(pixels[bottom - 1][left:right]):
        bottom -= 1
    while left + 16 < right and uniform_edge(
        [pixels[row][left] for row in range(top, bottom)]
    ):
        left += 1
    while right - left > 16 and uniform_edge(
        [pixels[row][right - 1] for row in range(top, bottom)]
    ):
        right -= 1
    return left, top, right, bottom


def perceptual_hash(path):
    """Return a content-cropped 64-bit difference hash."""
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        run_sips("-Z", "72", "-s", "format", "bmp", path, "--out", temporary)
        pixels = bmp_pixels(temporary)
        left, top, right, bottom = content_bounds(pixels)
        cropped = [row[left:right] for row in pixels[top:bottom]]
        bits = 0
        for target_y in range(8):
            source_y = min(
                len(cropped) - 1,
                round(target_y * max(1, len(cropped) - 1) / 7),
            )
            samples = [
                cropped[source_y][
                    min(
                        len(cropped[0]) - 1,
                        round(target_x * max(1, len(cropped[0]) - 1) / 8),
                    )
                ]
                for target_x in range(9)
            ]
            for left_value, right_value in zip(samples, samples[1:]):
                bits = (bits << 1) | int(left_value > right_value)
        return "{:016x}".format(bits)
    finally:
        temporary.unlink(missing_ok=True)


def hamming_distance(left, right):
    return bin(int(left, 16) ^ int(right, 16)).count("1")


def empty_progress():
    return {
        "version": 1,
        "updatedAt": utc_now(),
        "archive": {},
        "items": {},
    }


def load_progress():
    if not PROGRESS_PATH.exists():
        return empty_progress()
    with PROGRESS_PATH.open(encoding="utf-8") as handle:
        progress = json.load(handle)
    if progress.get("version") != 1:
        raise RuntimeError("unsupported archive-work progress version")
    return progress


def save_progress(progress):
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    progress["updatedAt"] = utc_now()
    temporary = PROGRESS_PATH.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(progress, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, PROGRESS_PATH)


def display_path(path):
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "image"


def proxy_path_for(source, sha256):
    return VISION_DIR / "{}-{}.jpg".format(sha256[:12], slugify(source.stem))


def find_duplicate_hint(progress, sha256, image_hash):
    archive = progress.get("archive", {})
    if sha256 in archive:
        return {"kind": "identical", "distance": 0, **archive[sha256]}

    nearest = None
    for fingerprint in archive.values():
        distance = hamming_distance(image_hash, fingerprint["dhash"])
        if nearest is None or distance < nearest[0]:
            nearest = (distance, fingerprint)
    if nearest and nearest[0] <= DUPLICATE_HINT_DISTANCE:
        return {"kind": "perceptual_hint", "distance": nearest[0], **nearest[1]}
    return None


def nearest_archive(progress, image_hash, limit=3):
    ranked = sorted(
        (
            (hamming_distance(image_hash, fingerprint["dhash"]), fingerprint)
            for fingerprint in progress.get("archive", {}).values()
        ),
        key=lambda value: value[0],
    )
    return [
        {
            "distance": distance,
            "path": fingerprint["path"],
            "sha256": fingerprint["sha256"],
        }
        for distance, fingerprint in ranked[:limit]
    ]


def prepare_one(progress, source, max_edge, quality, force):
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError("unsupported image extension: {}".format(source.suffix))

    sha256 = file_sha256(source)
    image_hash = perceptual_hash(source)
    proxy = proxy_path_for(source, sha256)
    VISION_DIR.mkdir(parents=True, exist_ok=True)
    existing = progress["items"].get(sha256)

    if (
        proxy.exists()
        and existing
        and existing.get("status") in {"analysis_saved", "imported"}
        and not force
    ):
        return {
            "sha256": sha256,
            "status": existing["status"],
            "proxy": display_path(proxy),
            "reused": True,
            "duplicateHint": find_duplicate_hint(progress, sha256, image_hash),
            "nearestArchive": nearest_archive(progress, image_hash),
        }

    raw_width, raw_height = image_dimensions(source)
    temporary = proxy.with_suffix(".jpg.tmp")
    try:
        if (
            source.suffix.lower() in {".jpg", ".jpeg"}
            and max(raw_width, raw_height) <= max_edge
            and source.stat().st_size <= PROXY_WARN_BYTES
        ):
            shutil.copyfile(source, temporary)
        else:
            run_sips(
                "-Z",
                str(max_edge),
                "-s",
                "format",
                "jpeg",
                "-s",
                "formatOptions",
                str(quality),
                source,
                "--out",
                temporary,
            )
        os.replace(temporary, proxy)
    finally:
        temporary.unlink(missing_ok=True)

    width, height = image_dimensions(proxy)
    proxy_bytes = proxy.stat().st_size
    status = existing.get("status", "prepared") if existing else "prepared"
    if status in {"analysis_saved", "imported"} and not force:
        status = existing["status"]

    progress["items"][sha256] = {
        "originalPath": str(source),
        "sha256": sha256,
        "dhash": image_hash,
        "dhashVersion": 2,
        "originalBytes": source.stat().st_size,
        "originalWidth": raw_width,
        "originalHeight": raw_height,
        "proxyPath": display_path(proxy),
        "proxyBytes": proxy_bytes,
        "proxyWidth": width,
        "proxyHeight": height,
        "status": status,
        "updatedAt": utc_now(),
    }
    save_progress(progress)
    return {
        "sha256": sha256,
        "status": status,
        "proxy": display_path(proxy),
        "proxyBytes": proxy_bytes,
        "proxyDimensions": [width, height],
        "oversizeWarning": proxy_bytes > PROXY_WARN_BYTES,
        "duplicateHint": find_duplicate_hint(progress, sha256, image_hash),
        "nearestArchive": nearest_archive(progress, image_hash),
    }


def seed_archive(progress, force):
    images_dir = ROOT / "images"
    if not images_dir.is_dir():
        raise FileNotFoundError(images_dir)

    added = 0
    updated = 0
    archive = progress.setdefault("archive", {})
    current_paths = set()
    for path in sorted(images_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        current_paths.add(display_path(path))
        sha256 = file_sha256(path)
        if sha256 in archive and not force:
            continue
        dhash = perceptual_hash(path)
        if sha256 in archive:
            updated += 1
        else:
            added += 1
        archive[sha256] = {
            "path": display_path(path),
            "sha256": sha256,
            "dhash": dhash,
            "dhashVersion": 2,
            "bytes": path.stat().st_size,
            "indexedAt": utc_now(),
        }
    for sha256, fingerprint in list(archive.items()):
        if (
            fingerprint.get("path", "").startswith("images/")
            and fingerprint["path"] not in current_paths
        ):
            del archive[sha256]
    save_progress(progress)
    return {
        "archiveFiles": len(archive),
        "added": added,
        "updated": updated,
        "progress": display_path(PROGRESS_PATH),
    }


def resolve_item(progress, reference):
    reference = reference.strip().lower()
    exact = progress["items"].get(reference)
    if exact:
        return reference, exact

    matches = [
        (sha256, item)
        for sha256, item in progress["items"].items()
        if sha256.startswith(reference)
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise KeyError("no progress item matches {!r}".format(reference))
    raise ValueError("hash prefix is ambiguous: {!r}".format(reference))


def mark_item(progress, reference, status, analysis, note):
    sha256, item = resolve_item(progress, reference)
    item["status"] = status
    item["updatedAt"] = utc_now()

    if analysis:
        analysis_path = Path(analysis).expanduser().resolve()
        if not analysis_path.is_file():
            raise FileNotFoundError(analysis_path)
        item["analysisPath"] = display_path(analysis_path)
    if note:
        item["note"] = note

    progress["items"][sha256] = item
    save_progress(progress)
    return {"sha256": sha256, **item}


def crop_item(progress, reference, height, width, offset_y, offset_x):
    sha256, item = resolve_item(progress, reference)
    proxy = ROOT / item["proxyPath"]
    if not proxy.is_file():
        raise FileNotFoundError(proxy)

    temporary = proxy.with_suffix(".jpg.tmp")
    try:
        run_sips(
            "-c",
            str(height),
            str(width),
            "--cropOffset",
            str(offset_y),
            str(offset_x),
            proxy,
            "--out",
            temporary,
        )
        os.replace(temporary, proxy)
    finally:
        temporary.unlink(missing_ok=True)

    width_after, height_after = image_dimensions(proxy)
    item["proxyBytes"] = proxy.stat().st_size
    item["proxyWidth"] = width_after
    item["proxyHeight"] = height_after
    item["crop"] = {
        "width": width,
        "height": height,
        "offsetX": offset_x,
        "offsetY": offset_y,
    }
    item["updatedAt"] = utc_now()
    progress["items"][sha256] = item
    save_progress(progress)
    return {
        "sha256": sha256,
        "proxyPath": item["proxyPath"],
        "proxyBytes": item["proxyBytes"],
        "proxyDimensions": [width_after, height_after],
        "crop": item["crop"],
    }


def sample_accent(progress, reference, x, y, radius):
    sha256, item = resolve_item(progress, reference)
    proxy = ROOT / item["proxyPath"]
    if not proxy.is_file():
        raise FileNotFoundError(proxy)

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        run_sips("-s", "format", "bmp", proxy, "--out", temporary)
        pixels = bmp_rgb_pixels(temporary)
    finally:
        temporary.unlink(missing_ok=True)

    height = len(pixels)
    width = len(pixels[0])
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError("sample point is outside the image")
    if radius < 0:
        raise ValueError("radius must be non-negative")

    left = max(0, x - radius)
    right = min(width, x + radius + 1)
    top = max(0, y - radius)
    bottom = min(height, y + radius + 1)
    samples = [
        pixels[row][column]
        for row in range(top, bottom)
        for column in range(left, right)
    ]
    red = round(sum(sample[0] for sample in samples) / len(samples))
    green = round(sum(sample[1] for sample in samples) / len(samples))
    blue = round(sum(sample[2] for sample in samples) / len(samples))
    accent = "#{:02X}{:02X}{:02X}".format(red, green, blue)
    item["accent"] = {"hex": accent, "x": x, "y": y, "radius": radius}
    item["updatedAt"] = utc_now()
    progress["items"][sha256] = item
    save_progress(progress)
    return {
        "sha256": sha256,
        "proxyPath": item["proxyPath"],
        "sample": item["accent"],
    }


def dominant_accent(progress, reference, minimum_chroma):
    sha256, item = resolve_item(progress, reference)
    proxy = ROOT / item["proxyPath"]
    if not proxy.is_file():
        raise FileNotFoundError(proxy)

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        run_sips("-s", "format", "bmp", proxy, "--out", temporary)
        pixels = bmp_rgb_pixels(temporary)
    finally:
        temporary.unlink(missing_ok=True)

    buckets = {}
    for row in pixels:
        for red, green, blue in row:
            chroma = max(red, green, blue) - min(red, green, blue)
            if chroma < minimum_chroma:
                continue
            key = (red // 16, green // 16, blue // 16)
            bucket = buckets.setdefault(
                key,
                {"count": 0, "score": 0, "red": 0, "green": 0, "blue": 0},
            )
            bucket["count"] += 1
            bucket["score"] += chroma * chroma
            bucket["red"] += red
            bucket["green"] += green
            bucket["blue"] += blue

    if not buckets:
        raise ValueError("no pixels meet the minimum chroma")
    selected = max(buckets.values(), key=lambda value: value["score"])
    red = round(selected["red"] / selected["count"])
    green = round(selected["green"] / selected["count"])
    blue = round(selected["blue"] / selected["count"])
    accent = "#{:02X}{:02X}{:02X}".format(red, green, blue)
    item["accent"] = {
        "hex": accent,
        "method": "dominant-chroma",
        "minimumChroma": minimum_chroma,
        "pixelCount": selected["count"],
    }
    item["updatedAt"] = utc_now()
    progress["items"][sha256] = item
    save_progress(progress)
    return {
        "sha256": sha256,
        "proxyPath": item["proxyPath"],
        "sample": item["accent"],
    }


def summarize(progress):
    counts = {status: 0 for status in sorted(STATUSES)}
    pending = []
    for sha256, item in progress["items"].items():
        status = item.get("status", "prepared")
        counts[status] = counts.get(status, 0) + 1
        if status not in {"analysis_saved", "imported", "skipped", "rejected"}:
            pending.append(
                {
                    "sha256": sha256,
                    "status": status,
                    "originalPath": item.get("originalPath"),
                    "proxyPath": item.get("proxyPath"),
                }
            )
    return {
        "archiveFingerprints": len(progress.get("archive", {})),
        "trackedItems": len(progress.get("items", {})),
        "counts": counts,
        "pending": pending,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Prepare compressed vision copies and record archive-work progress."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser(
        "seed-archive",
        help="index images/ once for byte and perceptual duplicate hints",
    )
    seed.add_argument("--force", action="store_true", help="recompute existing hashes")

    prepare = subparsers.add_parser(
        "prepare",
        help="create compressed JPEG working copies for one or more images",
    )
    prepare.add_argument("inputs", nargs="+", help="source image paths")
    prepare.add_argument("--max-edge", type=int, default=1300)
    prepare.add_argument("--quality", type=int, default=82)
    prepare.add_argument("--force", action="store_true")

    mark = subparsers.add_parser("mark", help="update one tracked image's status")
    mark.add_argument("reference", help="full SHA-256 or an unambiguous prefix")
    mark.add_argument("--status", required=True, choices=sorted(STATUSES))
    mark.add_argument("--analysis", help="path to the completed analysis JSON")
    mark.add_argument("--note", help="short handoff note")

    crop = subparsers.add_parser(
        "crop",
        help="visually verified crop operation for a prepared screenshot proxy",
    )
    crop.add_argument("reference", help="full SHA-256 or an unambiguous prefix")
    crop.add_argument("--width", type=int, required=True)
    crop.add_argument("--height", type=int, required=True)
    crop.add_argument("--offset-x", type=int, required=True)
    crop.add_argument("--offset-y", type=int, required=True)

    accent = subparsers.add_parser(
        "sample-accent",
        help="measure an accent colour from a region of a prepared image",
    )
    accent.add_argument("reference", help="full SHA-256 or an unambiguous prefix")
    accent.add_argument("--x", type=int, required=True)
    accent.add_argument("--y", type=int, required=True)
    accent.add_argument("--radius", type=int, default=8)

    dominant = subparsers.add_parser(
        "dominant-accent",
        help="measure the strongest repeated chromatic colour",
    )
    dominant.add_argument("reference", help="full SHA-256 or an unambiguous prefix")
    dominant.add_argument("--minimum-chroma", type=int, default=24)

    subparsers.add_parser("summary", help="show counts and unfinished items")
    return parser


def main():
    args = build_parser().parse_args()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    progress = load_progress()

    if args.command == "seed-archive":
        output = seed_archive(progress, args.force)
    elif args.command == "prepare":
        output = {
            "items": [
                prepare_one(progress, Path(value), args.max_edge, args.quality, args.force)
                for value in args.inputs
            ]
        }
    elif args.command == "mark":
        output = mark_item(
            progress,
            args.reference,
            args.status,
            args.analysis,
            args.note,
        )
    elif args.command == "crop":
        output = crop_item(
            progress,
            args.reference,
            args.height,
            args.width,
            args.offset_y,
            args.offset_x,
        )
    elif args.command == "sample-accent":
        output = sample_accent(
            progress,
            args.reference,
            args.x,
            args.y,
            args.radius,
        )
    elif args.command == "dominant-accent":
        output = dominant_accent(
            progress,
            args.reference,
            args.minimum_chroma,
        )
    elif args.command == "summary":
        output = summarize(progress)
    else:
        raise AssertionError(args.command)

    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
