#!/usr/bin/env python3
"""Shared helpers for the Ayou-Lab candidate review pipeline."""

import base64
import colorsys
import datetime as dt
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "entries.json"
IMAGES_DIR = ROOT / "images"
SPEC_PATH = ROOT / "docs" / "IMAGE_ANALYSIS_SPEC.md"

CATEGORIES = {"nature", "memory", "strange", "color", "dream"}
ANALYSIS_FIELDS = (
    "content",
    "composition",
    "color",
    "typography",
    "texture",
    "material",
    "spatialDepth",
    "hierarchy",
    "mood",
    "visualStyle",
    "interaction",
    "dna",
    "uncertainty",
)
PROVENANCE_FIELDS = {
    "provider",
    "sourceId",
    "sourcePage",
    "imageUrl",
    "creator",
    "sourceDate",
    "license",
    "licenseUrl",
    "rightsStatus",
    "verifiedAt",
    "evidence",
}
PUBLIC_DOMAIN_STATUSES = {"public_domain", "cc0"}
ALLOWED_HOSTS = {
    "aic": {"www.artic.edu", "api.artic.edu", "iiif.artic.edu"},
    "wikimedia": {
        "commons.wikimedia.org",
        "upload.wikimedia.org",
        "thumb.wikimedia.org",
    },
}
USER_AGENT = (
    "Ayou-Lab/1.0 "
    "(https://github.com/jingyouyuan62-ayou/ayou-lab; archive candidate workflow)"
)
AIC_API = "https://api.artic.edu/api/v1/artworks"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
CANDIDATE_BLOCK_NAME = "AYOU_CANDIDATE_V1"
CANDIDATE_BLOCK_RE = re.compile(
    r"<!--\s*AYOU_CANDIDATE_V1\s*\n(?P<data>[A-Za-z0-9+/=\s]+)\n-->",
    re.MULTILINE,
)


class CandidateError(ValueError):
    """Raised when a generated or approved candidate is unsafe or incomplete."""


def today_shanghai():
    return dt.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_html(value):
    if value is None:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def wikimedia_license_allowed(extmetadata):
    if not isinstance(extmetadata, dict):
        return None
    license_key = clean_html(extmetadata.get("License", {}).get("value")).lower()
    short_name = clean_html(
        extmetadata.get("LicenseShortName", {}).get("value")
    ).lower()
    if license_key.startswith("cc0") or "cc0" in short_name:
        return "cc0"
    if license_key.startswith("pd") or short_name.startswith("public domain"):
        return "public_domain"
    return None


def verify_current_rights(candidate):
    """Re-query the provider and return fresh evidence for the import record."""
    source = candidate["source"]
    provider = source["provider"]
    source_id = str(source["sourceId"])

    if provider == "aic":
        query = urlencode({"fields": "id,is_public_domain,image_id"})
        payload = http_json("{}/{}?{}".format(AIC_API, source_id, query))
        work = payload.get("data")
        if not isinstance(work, dict) or str(work.get("id")) != source_id:
            raise CandidateError("Art Institute source record could not be verified")
        if work.get("is_public_domain") is not True:
            raise CandidateError(
                "Art Institute source is no longer marked public domain"
            )
        image_id = work.get("image_id")
        if image_id and "/iiif/2/{}/".format(image_id) not in source["imageUrl"]:
            raise CandidateError("Art Institute image does not match its source record")
        return (
            "At approval, the Art Institute of Chicago public API again "
            "reported is_public_domain=true for this artwork."
        )

    if provider == "wikimedia":
        try:
            page_id = int(source_id)
        except ValueError as exc:
            raise CandidateError("Wikimedia source id is not a page id") from exc
        params = urlencode(
            {
                "action": "query",
                "pageids": str(page_id),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "format": "json",
                "formatversion": "2",
            }
        )
        payload = http_json("{}?{}".format(WIKIMEDIA_API, params))
        pages = payload.get("query", {}).get("pages", [])
        if (
            not isinstance(pages, list)
            or len(pages) != 1
            or str(pages[0].get("pageid")) != source_id
        ):
            raise CandidateError("Wikimedia source page could not be verified")
        infos = pages[0].get("imageinfo") or []
        if not infos or not isinstance(infos[0], dict):
            raise CandidateError("Wikimedia source has no current image metadata")
        metadata = infos[0].get("extmetadata") or {}
        rights_status = wikimedia_license_allowed(metadata)
        if rights_status not in PUBLIC_DOMAIN_STATUSES:
            raise CandidateError(
                "Wikimedia source is no longer marked Public Domain or CC0"
            )
        license_name = (
            clean_html(metadata.get("LicenseShortName", {}).get("value"))
            or rights_status.replace("_", " ").title()
        )
        return (
            "At approval, Wikimedia Commons again identified this file as {}."
        ).format(license_name)

    raise CandidateError("Unsupported candidate source provider: {}".format(provider))


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug[:80].strip("-") or "untitled"


def require_https_host(url, provider):
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or not parsed.hostname:
        raise CandidateError("URL must be an absolute HTTPS URL: {}".format(url))
    allowed = ALLOWED_HOSTS.get(provider)
    if allowed and parsed.hostname not in allowed:
        raise CandidateError(
            "URL host is not allowed for {}: {}".format(provider, parsed.hostname)
        )


def http_request(
    url,
    *,
    method="GET",
    headers=None,
    body=None,
    timeout=90,
    max_bytes=40 * 1024 * 1024,
):
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }
    if headers:
        request_headers.update(headers)
    for attempt in range(3):
        request = Request(
            url,
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                final_url = response.geturl()
                chunks = []
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise CandidateError(
                            "Response exceeds {} bytes: {}".format(max_bytes, url)
                        )
                    chunks.append(chunk)
                return b"".join(chunks), response.headers, final_url
        except HTTPError as exc:
            detail = exc.read(2000).decode("utf-8", errors="replace")
            if (
                method.upper() == "GET"
                and exc.code in {429, 503}
                and attempt < 2
            ):
                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 2**attempt
                except ValueError:
                    delay = 2**attempt
                time.sleep(max(1, min(delay, 8)))
                continue
            raise CandidateError(
                "HTTP {} for {}: {}".format(exc.code, url, detail)
            ) from exc
        except URLError as exc:
            raise CandidateError(
                "Network error for {}: {}".format(url, exc)
            ) from exc
    raise CandidateError("Request retries exhausted for {}".format(url))


def http_json(url, **kwargs):
    data, _, _ = http_request(url, **kwargs)
    return json.loads(data.decode("utf-8"))


def fetch_image(url, provider):
    require_https_host(url, provider)
    data, headers, final_url = http_request(url, max_bytes=40 * 1024 * 1024)
    require_https_host(final_url, provider)
    content_type = headers.get("Content-Type", "")
    if content_type and not content_type.lower().startswith("image/"):
        raise CandidateError(
            "Candidate URL did not return an image: {}".format(content_type)
        )
    return data


def github_api(method, path, *, token, payload=None):
    api_url = "https://api.github.com{}".format(path)
    body = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer {}".format(token),
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    data, _, _ = http_request(
        api_url,
        method=method,
        headers=headers,
        body=body,
        timeout=90,
        max_bytes=10 * 1024 * 1024,
    )
    return json.loads(data.decode("utf-8")) if data else None


def encode_candidate_block(candidate):
    raw = json.dumps(
        candidate,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii")
    return "<!-- {}\n{}\n-->".format(CANDIDATE_BLOCK_NAME, encoded)


def decode_candidate_block(body):
    match = CANDIDATE_BLOCK_RE.search(body or "")
    if not match:
        raise CandidateError("Issue does not contain an Ayou-Lab candidate record")
    encoded = re.sub(r"\s+", "", match.group("data"))
    try:
        raw = base64.b64decode(encoded, validate=True)
        decoded = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise CandidateError("Candidate record cannot be decoded") from exc
    validate_candidate(decoded)
    return decoded


def _nonempty_string(value, label, minimum=1, maximum=None):
    if not isinstance(value, str):
        raise CandidateError("{} must be a string".format(label))
    text = value.strip()
    if len(text) < minimum:
        raise CandidateError("{} is too short".format(label))
    if maximum is not None and len(text) > maximum:
        raise CandidateError("{} is too long".format(label))
    return text


def validate_candidate(candidate):
    if not isinstance(candidate, dict):
        raise CandidateError("Candidate must be an object")
    if candidate.get("schemaVersion") != 1:
        raise CandidateError("Unsupported candidate schemaVersion")

    title = _nonempty_string(candidate.get("title"), "title", 2, 80)
    words = title.split()
    if not 1 <= len(words) <= 5:
        raise CandidateError("title must contain 1-5 words")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9' &-]*", title):
        raise CandidateError("title must use plain English words")

    category = candidate.get("category")
    if not isinstance(category, str) or category not in CATEGORIES:
        raise CandidateError("category is invalid")

    medium = _nonempty_string(candidate.get("medium"), "medium", 2, 40)
    note = _nonempty_string(candidate.get("note"), "note", 8, 260)
    if "\n" in note:
        raise CandidateError("note must be one line")
    fit_score = candidate.get("fitScore")
    if not isinstance(fit_score, int) or not 0 <= fit_score <= 100:
        raise CandidateError("fitScore must be an integer from 0 to 100")
    _nonempty_string(candidate.get("fitReason"), "fitReason", 8, 500)

    tags = candidate.get("tags")
    if (
        not isinstance(tags, list)
        or not 2 <= len(tags) <= 8
        or not all(isinstance(item, str) and item.strip() for item in tags)
    ):
        raise CandidateError("tags must be a 2-8 item string array")

    echoes = candidate.get("echoes")
    if not isinstance(echoes, dict):
        raise CandidateError("echoes must be an object")
    candidates = echoes.get("candidates")
    if not isinstance(candidates, list) or not all(
        isinstance(item, str) and item.strip() for item in candidates
    ):
        raise CandidateError("echoes.candidates must be a string array")
    if echoes.get("confirmed") != []:
        raise CandidateError(
            "echoes.confirmed must be empty before the owner approves it"
        )

    analysis = candidate.get("analysis")
    if not isinstance(analysis, dict):
        raise CandidateError("analysis must be an object")
    missing = set(ANALYSIS_FIELDS) - set(analysis)
    extra = set(analysis) - set(ANALYSIS_FIELDS)
    if missing or extra:
        raise CandidateError(
            "analysis fields mismatch; missing={}, extra={}".format(
                sorted(missing), sorted(extra)
            )
        )
    for field in ANALYSIS_FIELDS:
        _nonempty_string(analysis[field], "analysis.{}".format(field), 8, 2000)

    accent = candidate.get("accent")
    if not isinstance(accent, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", accent):
        raise CandidateError("accent must be a measured #RRGGBB value")
    fingerprint = candidate.get("fingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(
        r"[0-9a-f]{16}", fingerprint
    ):
        raise CandidateError("fingerprint must be a 16-character dHash")

    source_key = _nonempty_string(candidate.get("sourceKey"), "sourceKey", 3, 200)
    source = candidate.get("source")
    if not isinstance(source, dict):
        raise CandidateError("source must be an object")
    provider = _nonempty_string(source.get("provider"), "source.provider")
    if source_key.split(":", 1)[0] != provider:
        raise CandidateError("sourceKey provider does not match source.provider")
    for field in (
        "title",
        "author",
        "date",
        "license",
        "licenseEvidence",
        "rightsStatus",
    ):
        _nonempty_string(source.get(field), "source.{}".format(field))
    if source["rightsStatus"].lower() not in PUBLIC_DOMAIN_STATUSES:
        raise CandidateError("Only public-domain or CC0 candidates may be approved")
    for field in ("pageUrl", "imageUrl"):
        require_https_host(source.get(field), provider)
    require_https_host(source.get("licenseUrl"), None)

    metrics = candidate.get("image")
    if not isinstance(metrics, dict):
        raise CandidateError("image metrics are missing")
    for field in ("width", "height", "sha256"):
        if field not in metrics:
            raise CandidateError("image.{} is missing".format(field))
    if not isinstance(metrics["width"], int) or metrics["width"] < 400:
        raise CandidateError("candidate image is too narrow")
    if not isinstance(metrics["height"], int) or metrics["height"] < 400:
        raise CandidateError("candidate image is too short")
    if not isinstance(metrics["sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", metrics["sha256"]
    ):
        raise CandidateError("image.sha256 is invalid")
    encoded_size = len(
        json.dumps(candidate, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    if encoded_size > 28000:
        raise CandidateError("Candidate record is too large for one GitHub Issue")
    return candidate


def load_entries(path=DATA_PATH):
    with Path(path).open(encoding="utf-8") as handle:
        entries = json.load(handle)
    if not isinstance(entries, list):
        raise CandidateError("entries.json must be a JSON array")
    return entries


def append_entry(path, entry):
    """Append one entry without re-serialising the existing archive array."""
    path = Path(path)
    original = path.read_text(encoding="utf-8")
    stripped = original.rstrip()
    if not stripped.endswith("]"):
        raise CandidateError("entries.json does not end with an array")
    closing = original.rfind("]")
    prefix = original[:closing].rstrip()
    suffix = original[closing + 1 :]
    serialized = json.dumps(entry, ensure_ascii=False, indent=2)
    indented = "\n".join("  " + line for line in serialized.splitlines())

    if prefix.endswith("["):
        updated = "{}\n{}\n]{}\n".format(prefix, indented, suffix.strip())
    else:
        if not prefix.endswith(","):
            prefix += ","
        updated = "{}\n{}\n]{}\n".format(prefix, indented, suffix.strip())

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(updated)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def make_provenance(candidate, verified_at):
    source = candidate["source"]
    return {
        "provider": source["provider"],
        "sourceId": source["sourceId"],
        "sourcePage": source["pageUrl"],
        "imageUrl": source["imageUrl"],
        "creator": source["author"],
        "sourceDate": source["date"],
        "license": source["license"],
        "licenseUrl": source["licenseUrl"],
        "rightsStatus": source["rightsStatus"],
        "verifiedAt": verified_at,
        "evidence": source["licenseEvidence"],
    }


def build_entry(candidate, *, image_path, accent, imported_at, issue_number):
    validate_candidate(candidate)
    id_value = slugify(candidate["title"])
    return {
        "id": id_value,
        "title": candidate["title"],
        "date": imported_at,
        "source": "collected",
        "medium": candidate["medium"],
        "category": candidate["category"],
        "tags": candidate["tags"],
        "note": candidate["note"],
        "image": image_path,
        "accent": accent,
        "echoes": {
            "candidates": candidate["echoes"]["candidates"],
            "confirmed": [],
        },
        "analysis": {
            field: candidate["analysis"][field] for field in ANALYSIS_FIELDS
        },
        "provenance": make_provenance(candidate, imported_at),
        "candidateIssue": issue_number,
    }


def _pillow_modules():
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise CandidateError(
            "Pillow is required for image validation; run "
            "'python3 -m pip install -r requirements.txt'"
        ) from exc
    return Image, ImageOps


def _sips_path():
    return shutil.which("sips")


def _temporary_image(data):
    if data.startswith(b"\xff\xd8"):
        suffix = ".jpg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        suffix = ".png"
    elif data.startswith((b"GIF87a", b"GIF89a")):
        suffix = ".gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        suffix = ".webp"
    else:
        suffix = ".img"
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    handle.write(data)
    handle.close()
    return Path(handle.name)


def _temporary_path(suffix):
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    handle.close()
    return Path(handle.name)


def _sips(*args):
    executable = _sips_path()
    if not executable:
        raise CandidateError("sips is unavailable")
    result = subprocess.run(
        [executable, *map(str, args)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _bmp_rgb_pixels(path):
    data = Path(path).read_bytes()
    if data[:2] != b"BM":
        raise CandidateError("sips did not produce a BMP image")
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size < 40:
        raise CandidateError("Unsupported BMP header")
    width = struct.unpack_from("<i", data, 18)[0]
    signed_height = struct.unpack_from("<i", data, 22)[0]
    bits_per_pixel = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if width <= 0 or signed_height == 0 or bits_per_pixel not in {24, 32}:
        raise CandidateError("Unsupported BMP layout")
    if compression not in {0, 3}:
        raise CandidateError("Unsupported BMP compression")
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
    return width, height, rows


def _bounds_from_rgb(width, height, pixels):
    rows = [
        [round(0.299 * red + 0.587 * green + 0.114 * blue) for red, green, blue in row]
        for row in pixels
    ]

    def uniform(values):
        ordered = sorted(values)
        median = ordered[len(ordered) // 2]
        return sum(abs(value - median) <= 18 for value in values) / len(values) >= 0.90

    top, bottom, left, right = 0, height, 0, width
    while top + 8 < bottom and uniform(rows[top][left:right]):
        top += 1
    while bottom - top > 8 and uniform(rows[bottom - 1][left:right]):
        bottom -= 1
    while left + 8 < right and uniform(
        [rows[row][left] for row in range(top, bottom)]
    ):
        left += 1
    while right - left > 8 and uniform(
        [rows[row][right - 1] for row in range(top, bottom)]
    ):
        right -= 1
    return left, top, right, bottom


def _sips_inspect(data):
    temporary = _temporary_image(data)
    bmp = _temporary_path(".bmp")
    try:
        dimensions = _sips(
            "-g", "pixelWidth", "-g", "pixelHeight", temporary
        )
        width_match = re.search(r"pixelWidth:\s*(\d+)", dimensions)
        height_match = re.search(r"pixelHeight:\s*(\d+)", dimensions)
        if not width_match or not height_match:
            raise CandidateError("Could not read image dimensions")
        original_width = int(width_match.group(1))
        original_height = int(height_match.group(1))
        _sips("-Z", "128", "-s", "format", "bmp", temporary, "--out", bmp)
        width, height, pixels = _bmp_rgb_pixels(bmp)
        left, top, right, bottom = _bounds_from_rgb(width, height, pixels)
        cropped = [row[left:right] for row in pixels[top:bottom]]
        if not cropped or not cropped[0]:
            cropped = pixels

        bits = 0
        for target_y in range(8):
            source_y = min(
                len(cropped) - 1,
                round(target_y * max(1, len(cropped) - 1) / 7),
            )
            row = cropped[source_y]
            values = []
            for target_x in range(9):
                red, green, blue = row[
                    min(
                        len(row) - 1,
                        round(target_x * max(1, len(row) - 1) / 8),
                    )
                ]
                values.append(round(0.299 * red + 0.587 * green + 0.114 * blue))
            for left_value, right_value in zip(values, values[1:]):
                bits = (bits << 1) | int(left_value > right_value)

        counts = {}
        for row in pixels:
            for red, green, blue in row:
                color = (
                    min(255, round(red / 32) * 32),
                    min(255, round(green / 32) * 32),
                    min(255, round(blue / 32) * 32),
                )
                counts[color] = counts.get(color, 0) + 1
        accent = None
        fallback = None
        for color, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True):
            red, green, blue = color
            _, saturation, value = colorsys.rgb_to_hsv(
                red / 255.0, green / 255.0, blue / 255.0
            )
            if fallback is None:
                fallback = color
            if saturation >= 0.16 and 0.12 <= value <= 0.92:
                accent = color
                break
        accent = accent or fallback or (128, 128, 128)
        return {
            "width": original_width,
            "height": original_height,
            "sha256": sha256_bytes(data),
            "fingerprint": "{:016x}".format(bits),
            "accent": "#{:02X}{:02X}{:02X}".format(*accent),
        }
    finally:
        temporary.unlink(missing_ok=True)
        bmp.unlink(missing_ok=True)


def _resize(Image, image, size):
    method = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    copy = image.copy()
    copy.thumbnail(size, method)
    return copy


def _content_crop(image):
    Image, _ = _pillow_modules()
    gray = _resize(Image, image.convert("L"), (128, 128))
    width, height = gray.size
    pixels = list(gray.getdata())
    rows = [pixels[y * width : (y + 1) * width] for y in range(height)]

    def uniform(values):
        ordered = sorted(values)
        median = ordered[len(ordered) // 2]
        return sum(abs(value - median) <= 18 for value in values) / len(values) >= 0.90

    top, bottom, left, right = 0, height, 0, width
    while top + 8 < bottom and uniform(rows[top][left:right]):
        top += 1
    while bottom - top > 8 and uniform(rows[bottom - 1][left:right]):
        bottom -= 1
    while left + 8 < right and uniform(
        [rows[row][left] for row in range(top, bottom)]
    ):
        left += 1
    while right - left > 8 and uniform(
        [rows[row][right - 1] for row in range(top, bottom)]
    ):
        right -= 1
    if right <= left or bottom <= top:
        return (0, 0, image.width, image.height)
    scale_x = image.width / width
    scale_y = image.height / height
    return (
        int(left * scale_x),
        int(top * scale_y),
        int(right * scale_x),
        int(bottom * scale_y),
    )
def inspect_image_bytes(data):
    try:
        Image, ImageOps = _pillow_modules()
    except CandidateError:
        if _sips_path():
            return _sips_inspect(data)
        raise
    try:
        image = Image.open(io.BytesIO(data))
        if getattr(image, "is_animated", False):
            image.seek(0)
        image = ImageOps.exif_transpose(image).convert("RGB")
    except Exception as exc:
        raise CandidateError("Image cannot be decoded") from exc

    crop = _content_crop(image)
    content = image.crop(crop)
    hash_image = _resize(Image, content.convert("L"), (72, 72))
    hash_image = hash_image.resize((9, 8))
    values = list(hash_image.getdata())
    bits = 0
    for y in range(8):
        row = values[y * 9 : (y + 1) * 9]
        for left_value, right_value in zip(row, row[1:]):
            bits = (bits << 1) | int(left_value > right_value)
    fingerprint = "{:016x}".format(bits)

    sample = _resize(Image, image, (256, 256))
    quantized = sample.quantize(colors=24).convert("RGB")
    counts = {}
    for color in quantized.getdata():
        counts[color] = counts.get(color, 0) + 1
    accent = None
    fallback = None
    for color, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        red, green, blue = color
        _, saturation, value = colorsys.rgb_to_hsv(
            red / 255.0, green / 255.0, blue / 255.0
        )
        if fallback is None:
            fallback = color
        if saturation >= 0.16 and 0.12 <= value <= 0.92:
            accent = color
            break
    if accent is None:
        accent = fallback or (128, 128, 128)

    return {
        "width": image.width,
        "height": image.height,
        "sha256": sha256_bytes(data),
        "fingerprint": fingerprint,
        "accent": "#{:02X}{:02X}{:02X}".format(*accent),
    }


def hamming_distance(left, right):
    return bin(int(left, 16) ^ int(right, 16)).count("1")


def nearest_archive_matches(fingerprint, images_dir=IMAGES_DIR, limit=3):
    ranked = []
    for path in sorted(Path(images_dir).iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            continue
        try:
            metrics = inspect_image_bytes(path.read_bytes())
        except CandidateError:
            continue
        ranked.append(
            {
                "image": str(path.relative_to(ROOT)),
                "distance": hamming_distance(fingerprint, metrics["fingerprint"]),
            }
        )
    ranked.sort(key=lambda item: item["distance"])
    return ranked[:limit]


def save_jpeg_bytes(data, max_edge=2400, quality=92):
    try:
        Image, ImageOps = _pillow_modules()
    except CandidateError:
        if not _sips_path():
            raise
        source = _temporary_image(data)
        target = _temporary_path(".jpg")
        try:
            _sips(
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
                target,
            )
            return target.read_bytes()
        finally:
            source.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
    try:
        image = Image.open(io.BytesIO(data))
        if getattr(image, "is_animated", False):
            image.seek(0)
        image = ImageOps.exif_transpose(image)
        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, (247, 244, 237))
            alpha = image.getchannel("A")
            background.paste(image.convert("RGB"), mask=alpha)
            image = background
        else:
            image = image.convert("RGB")
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )
        return output.getvalue()
    except Exception as exc:
        raise CandidateError("Image cannot be converted to JPEG") from exc


def markdown_escape(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
    )
