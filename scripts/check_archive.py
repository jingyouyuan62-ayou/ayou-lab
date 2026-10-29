#!/usr/bin/env python3
"""Structural checks for Ayou-Lab's archive data.

This validates the data layer only. The 16-field image analysis is checked
manually against docs/IMAGE_ANALYSIS_SPEC.md.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from collections import Counter
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "entries.json")
IMAGES_DIR = os.path.join(ROOT, "images")

CATEGORIES = {"nature", "memory", "strange", "color", "dream"}
SOURCES = {"own", "collected"}
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
ANALYSIS_SOURCE_FIELDS = {
    "type",
    "sessionId",
    "messageId",
    "timestamp",
    "sourceTitle",
    "originalArtifact",
    "originalSha256",
    "sourceFormat",
    "mappingVersion",
}
ANALYSIS_SOURCE_FORMATS = {
    "structured_json",
    "structured_markdown",
    "dense_prose",
}
PROVENANCE_REQUIRED = {
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
PROVENANCE_OPTIONAL = {"finalSha256", "finalDimensions"}
PUBLIC_DOMAIN_STATUSES = {"public_domain", "cc0"}
REQUIRED = {
    "id": str,
    "title": str,
    "date": str,
    "source": str,
    "medium": str,
    "category": str,
    "note": str,
    "image": str,
    "accent": str,
}
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def string_list(value):
    return isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def main():
    parser = argparse.ArgumentParser(
        description="Check Ayou-Lab archive structure and analysis objects."
    )
    parser.add_argument(
        "--strict-analysis",
        action="store_true",
        help="fail if any entry has no analysis object (legacy entries included)",
    )
    args = parser.parse_args()

    errors = []
    warnings = []

    def error(message):
        errors.append(message)

    def warn(message):
        warnings.append(message)

    try:
        with open(DATA_PATH, encoding="utf-8") as handle:
            entries = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print("ERROR: cannot read data/entries.json: {}".format(exc))
        return 1

    if not isinstance(entries, list):
        print("ERROR: data/entries.json must be a JSON array")
        return 1

    seen_ids = Counter()
    seen_titles = Counter()
    referenced_images = set()
    analysis_count = 0

    for index, entry in enumerate(entries):
        label = "entry[{}]".format(index)
        if not isinstance(entry, dict):
            error("{} is not an object".format(label))
            continue

        entry_id = entry.get("id")
        if isinstance(entry_id, str):
            label = "{} ({})".format(label, entry_id)

        for field, expected_type in REQUIRED.items():
            if field not in entry:
                error("{}: missing '{}'".format(label, field))
            elif not isinstance(entry[field], expected_type):
                error(
                    "{}: '{}' must be {}, got {}".format(
                        label, field, expected_type.__name__, type(entry[field]).__name__
                    )
                )
            elif expected_type is str and not entry[field].strip():
                error("{}: '{}' is empty".format(label, field))

        if isinstance(entry_id, str):
            seen_ids[entry_id] += 1
            if not KEBAB.match(entry_id):
                error("{}: id is not kebab-case".format(label))

        title = entry.get("title")
        if isinstance(title, str) and title.strip():
            seen_titles[title.strip().lower()] += 1
            if not 1 <= len(title.split()) <= 5:
                error("{}: title must be 1-5 words".format(label))

        date = entry.get("date")
        if isinstance(date, str) and date.strip():
            if not DATE.match(date):
                error("{}: date must be YYYY-MM-DD".format(label))
            else:
                try:
                    datetime.date.fromisoformat(date)
                except ValueError:
                    error("{}: date is not a real calendar date".format(label))

        source = entry.get("source")
        if isinstance(source, str) and source not in SOURCES:
            error("{}: source must be one of {}".format(label, sorted(SOURCES)))

        category = entry.get("category")
        if isinstance(category, str) and category not in CATEGORIES:
            error("{}: category must be one of {}".format(label, sorted(CATEGORIES)))

        accent = entry.get("accent")
        if isinstance(accent, str) and not HEX.match(accent):
            error("{}: accent must be #RRGGBB".format(label))

        note = entry.get("note")
        if isinstance(note, str) and len(note.strip()) < 8:
            warn("{}: note looks too short to be useful".format(label))

        image = entry.get("image")
        if isinstance(image, str) and image.strip():
            referenced_images.add(os.path.normpath(image))
            if not image.startswith("images/"):
                error("{}: image must live under images/".format(label))
            if not os.path.exists(os.path.join(ROOT, image)):
                error("{}: image does not exist: {}".format(label, image))
            stem = os.path.splitext(os.path.basename(image))[0]
            if isinstance(entry_id, str) and stem.lower() != entry_id.lower():
                error("{}: filename stem '{}' does not match id".format(label, stem))

        if "tags" in entry:
            if not string_list(entry["tags"]):
                error("{}: tags must be a non-empty array of strings".format(label))

        if "ideas" in entry:
            if not string_list(entry["ideas"]):
                error("{}: ideas must be an array of strings".format(label))

        if "echoes" in entry and entry["echoes"] is not None:
            echoes = entry["echoes"]
            if not isinstance(echoes, dict):
                error("{}: echoes must be an object".format(label))
            else:
                extra = set(echoes) - {"candidates", "confirmed"}
                if extra:
                    warn("{}: unexpected echoes keys {}".format(label, sorted(extra)))
                for key in ("candidates", "confirmed"):
                    if key not in echoes:
                        error("{}: echoes missing '{}'".format(label, key))
                    elif not string_list(echoes[key]):
                        error(
                            "{}: echoes.{} must be an array of strings".format(label, key)
                        )

        if "analysis" in entry and entry["analysis"] is not None:
            analysis = entry["analysis"]
            if not isinstance(analysis, dict):
                error("{}: analysis must be an object".format(label))
            else:
                analysis_count += 1
                for field in ANALYSIS_FIELDS:
                    if field not in analysis:
                        error("{}: analysis missing '{}'".format(label, field))
                        continue
                    value = analysis[field]
                    if not isinstance(value, str) or not value.strip():
                        error(
                            "{}: analysis.{} must be a non-empty string".format(
                                label, field
                            )
                        )
                        continue
                    text = value.strip()
                    no_text_note = field == "typography" and (
                        "无文字" in text or "没有文字" in text or "无可读文字" in text
                    )
                    if len(text) < 20 and not no_text_note:
                        warn(
                            "{}: analysis.{} looks too short for the required depth".format(
                                label, field
                            )
                        )
                extra = set(analysis) - set(ANALYSIS_FIELDS)
                if extra:
                    warn(
                        "{}: analysis has unexpected keys {}".format(
                            label, sorted(extra)
                        )
                    )
                dna = analysis.get("dna")
                if isinstance(dna, str) and dna.strip():
                    lowered = dna.lower()
                    if not any(name in lowered for name in CATEGORIES):
                        warn(
                            "{}: analysis.dna does not name a known category".format(
                                label
                            )
                        )

        if "analysisSource" in entry:
            if entry.get("analysis") is None:
                error("{}: analysisSource requires analysis".format(label))
            source = entry["analysisSource"]
            if not isinstance(source, dict):
                error("{}: analysisSource must be an object".format(label))
            else:
                missing = ANALYSIS_SOURCE_FIELDS - set(source)
                extra = set(source) - ANALYSIS_SOURCE_FIELDS
                if missing:
                    error(
                        "{}: analysisSource missing {}".format(
                            label, sorted(missing)
                        )
                    )
                if extra:
                    error(
                        "{}: analysisSource has unexpected keys {}".format(
                            label, sorted(extra)
                        )
                    )
                if source.get("type") != "historical_chat_recovery":
                    error("{}: analysisSource.type is invalid".format(label))
                if source.get("sourceFormat") not in ANALYSIS_SOURCE_FORMATS:
                    error("{}: analysisSource.sourceFormat is invalid".format(label))
                if source.get("mappingVersion") != "2026-10-26.v2.1":
                    error("{}: analysisSource.mappingVersion is invalid".format(label))
                timestamp = source.get("timestamp")
                try:
                    datetime.datetime.fromisoformat(
                        str(timestamp).replace("Z", "+00:00")
                    )
                except ValueError:
                    error("{}: analysisSource.timestamp is invalid".format(label))
                if not isinstance(source.get("sourceTitle"), str) or not source.get(
                    "sourceTitle", ""
                ).strip():
                    error("{}: analysisSource.sourceTitle is empty".format(label))
                original = source.get("originalArtifact")
                if not isinstance(original, str) or not original.startswith(
                    "docs/analysis-recovery/original/"
                ):
                    error(
                        "{}: analysisSource.originalArtifact must be under "
                        "docs/analysis-recovery/original/".format(label)
                    )
                else:
                    original_path = os.path.join(ROOT, original)
                    if not os.path.isfile(original_path):
                        error(
                            "{}: analysisSource artifact does not exist: {}".format(
                                label, original
                            )
                        )
                    else:
                        expected_hash = source.get("originalSha256")
                        if not isinstance(expected_hash, str) or not SHA256.match(
                            expected_hash
                        ):
                            error(
                                "{}: analysisSource.originalSha256 is invalid".format(
                                    label
                                )
                            )
                        elif file_sha256(original_path) != expected_hash:
                            error(
                                "{}: analysisSource artifact hash mismatch".format(
                                    label
                                )
                            )

        if "provenance" in entry:
            if entry.get("analysis") is None:
                error("{}: provenance requires analysis".format(label))
            provenance = entry["provenance"]
            if not isinstance(provenance, dict):
                error("{}: provenance must be an object".format(label))
            else:
                missing = PROVENANCE_REQUIRED - set(provenance)
                extra = set(provenance) - PROVENANCE_REQUIRED - PROVENANCE_OPTIONAL
                if missing:
                    error(
                        "{}: provenance missing {}".format(label, sorted(missing))
                    )
                if extra:
                    error(
                        "{}: provenance has unexpected keys {}".format(
                            label, sorted(extra)
                        )
                    )
                for field in PROVENANCE_REQUIRED:
                    value = provenance.get(field)
                    if not isinstance(value, str) or not value.strip():
                        error(
                            "{}: provenance.{} must be a non-empty string".format(
                                label, field
                            )
                        )
                if provenance.get("rightsStatus") not in PUBLIC_DOMAIN_STATUSES:
                    error(
                        "{}: provenance.rightsStatus must be public_domain or cc0".format(
                            label
                        )
                    )
                for field in ("sourcePage", "imageUrl", "licenseUrl"):
                    value = provenance.get(field)
                    parsed = urlparse(value) if isinstance(value, str) else None
                    if parsed is None or parsed.scheme != "https" or not parsed.netloc:
                        error(
                            "{}: provenance.{} must be an HTTPS URL".format(
                                label, field
                            )
                        )
                final_hash = provenance.get("finalSha256")
                if final_hash is not None and (
                    not isinstance(final_hash, str) or not SHA256.match(final_hash)
                ):
                    error("{}: provenance.finalSha256 is invalid".format(label))

        if "candidateIssue" in entry and (
            not isinstance(entry["candidateIssue"], int) or entry["candidateIssue"] < 1
        ):
            error("{}: candidateIssue must be a positive integer".format(label))

    for entry_id, count in sorted(seen_ids.items()):
        if count > 1:
            error("duplicate id '{}' appears {} times".format(entry_id, count))

    for title, count in sorted(seen_titles.items()):
        if count > 1:
            error("duplicate title '{}' appears {} times".format(title, count))

    if len(referenced_images) != len(entries):
        error(
            "{} entries but {} distinct image paths".format(
                len(entries), len(referenced_images)
            )
        )

    if os.path.isdir(IMAGES_DIR):
        files = {
            os.path.normpath(os.path.join("images", name))
            for name in os.listdir(IMAGES_DIR)
            if not name.startswith(".")
        }
        for orphan in sorted(files - referenced_images):
            error("image not referenced by entries.json: {}".format(orphan))
    else:
        error("images/ directory is missing")

    if args.strict_analysis and analysis_count != len(entries):
        error(
            "{} of {} entries have no analysis object (--strict-analysis)".format(
                len(entries) - analysis_count, len(entries)
            )
        )

    category_counts = Counter(
        entry.get("category") for entry in entries if isinstance(entry, dict)
    )

    for message in warnings:
        print("WARN: " + message)
    for message in errors:
        print("ERROR: " + message)

    print(
        "Checked {} entries, {} images, {} with analysis.".format(
            len(entries), len(referenced_images), analysis_count
        )
    )
    print(
        "Categories: "
        + ", ".join(
            "{}={}".format(name, category_counts.get(name, 0))
            for name in ("nature", "memory", "strange", "color", "dream")
        )
    )

    if errors:
        print("FAILED: {} error(s), {} warning(s)".format(len(errors), len(warnings)))
        return 1

    print("OK: {} warning(s)".format(len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
