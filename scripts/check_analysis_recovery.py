#!/usr/bin/env python3
"""Validate historical-analysis recovery drafts without modifying the archive."""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES_PATH = os.path.join(ROOT, "data", "entries.json")
MANIFEST_PATH = os.path.join(ROOT, "docs", "analysis-recovery", "manifest.json")
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
SOURCE_FORMATS = {"structured_json", "structured_markdown", "dense_prose"}
STATUSES = {"ready_for_review", "needs_owner_confirmation"}
ARCHIVE_STATUSES = {"pending", "imported"}
REANALYSIS_STATUSES = {"draft", "applied"}
SOURCE_FIELDS = {
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
UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser(
        description="Validate Ayou-Lab historical-analysis recovery drafts."
    )
    parser.add_argument("--entry", help="validate only one Archive entry id")
    args = parser.parse_args()

    errors = []
    warnings = []

    def error(message):
        errors.append(message)

    def warn(message):
        warnings.append(message)

    def validate_analysis_object(value, label):
        if not isinstance(value, dict):
            error("{} analysis must be an object".format(label))
            return
        if tuple(value) != ANALYSIS_FIELDS:
            error(
                "{} analysis keys must be exactly {}".format(
                    label, list(ANALYSIS_FIELDS)
                )
            )
        for field in ANALYSIS_FIELDS:
            field_value = value.get(field)
            if not isinstance(field_value, str) or not field_value.strip():
                error(
                    "{} analysis.{} must be a non-empty string".format(
                        label, field
                    )
                )

    try:
        entries = load_json(ENTRIES_PATH)
        manifest = load_json(MANIFEST_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        print("ERROR: cannot read recovery input: {}".format(exc))
        return 1

    if not isinstance(entries, list):
        print("ERROR: data/entries.json must be a JSON array")
        return 1
    if manifest.get("schemaVersion") != 1:
        error("manifest schemaVersion must be 1")
    samples = manifest.get("samples")
    if not isinstance(samples, list):
        print("ERROR: manifest.samples must be an array")
        return 1
    if args.entry:
        samples = [sample for sample in samples if sample.get("entryId") == args.entry]
        if not samples:
            print("ERROR: no recovery sample for entry '{}'".format(args.entry))
            return 1
    reanalyses = manifest.get("reanalyses", [])
    if not isinstance(reanalyses, list):
        print("ERROR: manifest.reanalyses must be an array")
        return 1
    if args.entry:
        reanalyses = [
            item for item in reanalyses if item.get("entryId") == args.entry
        ]

    formal_trial = manifest.get("formalTrial")
    if formal_trial is not None:
        if not isinstance(formal_trial, dict):
            error("manifest.formalTrial must be an object")
        else:
            trial_entries = formal_trial.get("entries")
            completed = formal_trial.get("completed")
            failed = formal_trial.get("failed")
            if not isinstance(trial_entries, list) or not all(
                isinstance(item, str) and item for item in trial_entries
            ):
                error("manifest.formalTrial.entries must be a string array")
            elif len(trial_entries) != len(set(trial_entries)):
                error("manifest.formalTrial.entries contains duplicates")
            elif completed != len(trial_entries):
                error("manifest.formalTrial.completed does not match entries")
            if not isinstance(failed, int) or failed < 0:
                error("manifest.formalTrial.failed must be a non-negative integer")
            all_samples = manifest.get("samples", [])
            imported_ids = {
                sample.get("entryId")
                for sample in all_samples
                if isinstance(sample, dict)
                and sample.get("archiveStatus") == "imported"
            }
            if isinstance(trial_entries, list):
                missing_imports = set(trial_entries) - imported_ids
                if missing_imports:
                    error(
                        "formalTrial completed entries are not marked imported: "
                        "{}".format(sorted(missing_imports))
                    )

    ids = collections.Counter(
        entry.get("id") for entry in entries if isinstance(entry, dict)
    )
    duplicate_ids = sorted(key for key, count in ids.items() if count > 1)
    if duplicate_ids:
        error("duplicate entry ids: {}".format(duplicate_ids))

    applied_reanalysis_analysis = {}
    seen_reanalyses = set()
    for index, record in enumerate(reanalyses):
        label = "reanalysis[{}]".format(index)
        if not isinstance(record, dict):
            error("{} is not an object".format(label))
            continue
        entry_id = record.get("entryId")
        if not isinstance(entry_id, str) or not entry_id:
            error("{} has no entryId".format(label))
            continue
        label = "{} ({})".format(label, entry_id)
        if entry_id in seen_reanalyses:
            error("{} is duplicated in manifest".format(label))
        seen_reanalyses.add(entry_id)

        status = record.get("status")
        if status not in REANALYSIS_STATUSES:
            error("{} has invalid status {}".format(label, status))
        reason = record.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            error("{} reason must be a non-empty string".format(label))
        authorized_at = record.get("authorizedAt")
        try:
            datetime.date.fromisoformat(str(authorized_at))
        except ValueError:
            error("{} authorizedAt must be YYYY-MM-DD".format(label))

        historical_draft_rel = record.get("historicalDraft")
        before_rel = record.get("beforeSnapshot")
        draft_rel = record.get("draft")
        for key, value in (
            ("historicalDraft", historical_draft_rel),
            ("beforeSnapshot", before_rel),
            ("draft", draft_rel),
        ):
            if not isinstance(value, str) or not value:
                error("{} has no {}".format(label, key))
        if not all(
            isinstance(value, str) and value
            for value in (historical_draft_rel, before_rel, draft_rel)
        ):
            continue

        historical_draft_path = os.path.join(ROOT, historical_draft_rel)
        before_path = os.path.join(ROOT, before_rel)
        draft_path = os.path.join(ROOT, draft_rel)
        for key, path in (
            ("historicalDraft", historical_draft_path),
            ("beforeSnapshot", before_path),
            ("draft", draft_path),
        ):
            if not os.path.isfile(path):
                error("{} {} does not exist: {}".format(label, key, path))
        if not all(
            os.path.isfile(path)
            for path in (historical_draft_path, before_path, draft_path)
        ):
            continue

        try:
            historical_draft = load_json(historical_draft_path)
            before = load_json(before_path)
            draft = load_json(draft_path)
        except (OSError, json.JSONDecodeError) as exc:
            error("{} cannot parse reanalysis input: {}".format(label, exc))
            continue

        entry = next(
            (item for item in entries if item.get("id") == entry_id), None
        )
        if entry is None:
            error("{} Archive entry does not exist".format(label))
            continue

        if historical_draft.get("entryId") != entry_id:
            error("{} historicalDraft entryId does not match".format(label))
        historical_patch = historical_draft.get("proposedPatch")
        if not isinstance(historical_patch, dict):
            error("{} historicalDraft proposedPatch must be an object".format(label))
            continue

        for artifact_name, artifact in (
            ("beforeSnapshot", before),
            ("draft", draft),
        ):
            if artifact.get("schemaVersion") != 1:
                error(
                    "{} {} schemaVersion must be 1".format(label, artifact_name)
                )
            if artifact.get("entryId") != entry_id:
                error(
                    "{} {} entryId does not match".format(label, artifact_name)
                )

        before_references = before.get("entryReferences")
        if not isinstance(before_references, dict):
            error("{} beforeSnapshot.entryReferences must be an object".format(label))
        else:
            for field in ("image", "title", "category", "accent"):
                if before_references.get(field) != entry.get(field):
                    error(
                        "{} beforeSnapshot.entryReferences.{} does not match "
                        "Archive".format(label, field)
                    )
            before_image_rel = before_references.get("image")
            before_image_path = (
                os.path.join(ROOT, before_image_rel)
                if isinstance(before_image_rel, str)
                else ""
            )
            if not os.path.isfile(before_image_path):
                error("{} beforeSnapshot image does not exist".format(label))
            elif before_references.get("imageSha256") != sha256(before_image_path):
                error("{} beforeSnapshot imageSha256 does not match".format(label))
            if before_references.get("echoes") != entry.get("echoes"):
                error(
                    "{} beforeSnapshot.entryReferences.echoes does not match "
                    "Archive".format(label)
                )

        before_analysis = before.get("analysis")
        validate_analysis_object(before_analysis, label + " beforeSnapshot")
        if before_analysis != historical_patch.get("analysis"):
            error(
                "{} beforeSnapshot analysis does not match historicalDraft".format(
                    label
                )
            )
        before_source = before.get("analysisSource")
        if before_source != historical_patch.get("analysisSource"):
            error(
                "{} beforeSnapshot analysisSource does not match "
                "historicalDraft".format(label)
            )

        image = draft.get("image")
        if not isinstance(image, dict):
            error("{} draft.image must be an object".format(label))
        else:
            image_rel = image.get("path")
            if image_rel != entry.get("image"):
                error("{} draft.image.path does not match Archive".format(label))
            image_path = (
                os.path.join(ROOT, image_rel)
                if isinstance(image_rel, str)
                else ""
            )
            if not os.path.isfile(image_path):
                error("{} draft image does not exist".format(label))
            elif image.get("sha256") != sha256(image_path):
                error("{} draft image.sha256 does not match".format(label))
            for dimension in ("width", "height"):
                if (
                    not isinstance(image.get(dimension), int)
                    or image.get(dimension) <= 0
                ):
                    error(
                        "{} draft.image.{} must be a positive integer".format(
                            label, dimension
                        )
                    )

        historical_trace = draft.get("historicalTrace")
        if not isinstance(historical_trace, dict):
            error("{} draft.historicalTrace must be an object".format(label))
            continue
        expected_trace_values = {
            "normalized": historical_draft_rel,
            "previousArchiveAnalysis": before_rel,
        }
        for key, expected in expected_trace_values.items():
            if historical_trace.get(key) != expected:
                error(
                    "{} draft.historicalTrace.{} does not match manifest".format(
                        label, key
                    )
                )
        for key, path in (
            ("original", historical_trace.get("original")),
            ("normalized", historical_trace.get("normalized")),
            ("previousArchiveAnalysis", historical_trace.get("previousArchiveAnalysis")),
        ):
            if not isinstance(path, str) or not os.path.isfile(os.path.join(ROOT, path)):
                error("{} draft.historicalTrace.{} does not exist".format(label, key))
        for key in ("originalSha256", "normalizedSha256"):
            value = historical_trace.get(key)
            if not isinstance(value, str) or not SHA256.match(value):
                error(
                    "{} draft.historicalTrace.{} is not a SHA-256".format(
                        label, key
                    )
                )
        original_rel = historical_trace.get("original")
        normalized_rel = historical_trace.get("normalized")
        if isinstance(original_rel, str) and os.path.isfile(
            os.path.join(ROOT, original_rel)
        ):
            if historical_trace.get("originalSha256") != sha256(
                os.path.join(ROOT, original_rel)
            ):
                error("{} historical original hash mismatch".format(label))
        if isinstance(normalized_rel, str) and os.path.isfile(
            os.path.join(ROOT, normalized_rel)
        ):
            if historical_trace.get("normalizedSha256") != sha256(
                os.path.join(ROOT, normalized_rel)
            ):
                error("{} historical normalized hash mismatch".format(label))

        prescribed_metadata = draft.get("preservedEntryMetadata")
        if not isinstance(prescribed_metadata, dict):
            error(
                "{} draft.preservedEntryMetadata must be an object".format(label)
            )
        else:
            for field in ("title", "category", "accent", "echoes"):
                if prescribed_metadata.get(field) != entry.get(field):
                    error(
                        "{} preservedEntryMetadata.{} does not match Archive".format(
                            label, field
                        )
                    )

        proposed_analysis = draft.get("proposedAnalysis")
        validate_analysis_object(proposed_analysis, label + " draft")
        if draft.get("kind") != "owner_authorized_image_reanalysis":
            error("{} draft.kind is invalid".format(label))
        if draft.get("status") != status:
            error("{} draft.status does not match manifest".format(label))
        try:
            datetime.date.fromisoformat(str(draft.get("createdAt")))
        except ValueError:
            error("{} draft.createdAt must be YYYY-MM-DD".format(label))

        comparison = draft.get("comparisonWithHistoricalDraft")
        if not isinstance(comparison, dict):
            error(
                "{} draft.comparisonWithHistoricalDraft must be an object".format(
                    label
                )
            )
        else:
            for key in (
                "preservedConclusions",
                "refinements",
                "changedVisualConclusions",
                "historicalInformationLost",
                "unsupportedAdditions",
            ):
                value = comparison.get(key)
                if not isinstance(value, list) or not all(
                    isinstance(item, str) and item.strip() for item in value
                ):
                    error(
                        "{} comparisonWithHistoricalDraft.{} must be a string "
                        "array".format(label, key)
                    )
            for key in (
                "changedVisualConclusions",
                "historicalInformationLost",
                "unsupportedAdditions",
            ):
                if comparison.get(key) != []:
                    error(
                        "{} comparisonWithHistoricalDraft.{} must be empty".format(
                            label, key
                        )
                    )

        validation = draft.get("validation")
        if not isinstance(validation, dict):
            error("{} draft.validation must be an object".format(label))
        else:
            for key in (
                "oneImageReadOnly",
                "allThirteenAnalysisFieldsPresent",
                "allValuesAreNonEmptyStrings",
                "imageAndHistoricalArtifactsTraceable",
                "preservedTitleCategoryAccentAndEchoes",
                "noUnsupportedConfirmedEchoes",
            ):
                if validation.get(key) is not True:
                    error("{} validation.{} must be true".format(label, key))

        if entry.get("analysisSource") != before_source:
            error(
                "{} Archive analysisSource no longer matches the preserved "
                "historical source".format(label)
            )
        if status == "draft":
            if entry.get("analysis") != before_analysis:
                error(
                    "{} draft exists but Archive analysis has already changed".format(
                        label
                    )
                )
        elif status == "applied":
            if entry.get("analysis") != proposed_analysis:
                error(
                    "{} applied reanalysis does not match Archive analysis".format(
                        label
                    )
                )
            applied_reanalysis_analysis[entry_id] = proposed_analysis

    seen_samples = set()
    for index, sample in enumerate(samples):
        label = "sample[{}]".format(index)
        if not isinstance(sample, dict):
            error("{} is not an object".format(label))
            continue
        entry_id = sample.get("entryId")
        if not isinstance(entry_id, str) or not entry_id:
            error("{} has no entryId".format(label))
            continue
        label = "{} ({})".format(label, entry_id)
        if entry_id in seen_samples:
            error("{} is duplicated in manifest".format(label))
        seen_samples.add(entry_id)

        status = sample.get("status")
        if status not in STATUSES:
            error("{} has invalid status {}".format(label, status))
        archive_status = sample.get("archiveStatus")
        if archive_status not in ARCHIVE_STATUSES:
            error("{} has invalid archiveStatus {}".format(label, archive_status))
        source_format = sample.get("sourceFormat")
        if source_format not in SOURCE_FORMATS:
            error("{} has invalid sourceFormat {}".format(label, source_format))

        normalized_rel = sample.get("normalized")
        original_rel = sample.get("original")
        validation_draft_rel = sample.get("validationDraft")
        if not isinstance(normalized_rel, str) or not normalized_rel:
            error("{} has no normalized path".format(label))
            continue
        if not isinstance(original_rel, str) or not original_rel:
            error("{} has no original path".format(label))
            continue
        normalized_path = os.path.join(ROOT, normalized_rel)
        original_path = os.path.join(ROOT, original_rel)
        if not os.path.isfile(original_path):
            error("{} original does not exist: {}".format(label, original_rel))
        if not os.path.isfile(normalized_path):
            error("{} normalized does not exist: {}".format(label, normalized_rel))
            continue
        if validation_draft_rel is not None:
            if not isinstance(validation_draft_rel, str) or not validation_draft_rel:
                error("{} validationDraft must be a non-empty path".format(label))
            elif not os.path.isfile(os.path.join(ROOT, validation_draft_rel)):
                error(
                    "{} validationDraft does not exist: {}".format(
                        label, validation_draft_rel
                    )
                )

        try:
            normalized = load_json(normalized_path)
        except (OSError, json.JSONDecodeError) as exc:
            error("{} cannot parse normalized JSON: {}".format(label, exc))
            continue

        if normalized.get("schemaVersion") != 1:
            error("{} normalized schemaVersion must be 1".format(label))
        if normalized.get("entryId") != entry_id:
            error("{} normalized entryId does not match manifest".format(label))
        if normalized.get("sourceFormat") != source_format:
            error("{} normalized sourceFormat does not match manifest".format(label))
        if normalized.get("status") != status:
            error("{} normalized status does not match manifest".format(label))

        patch = normalized.get("proposedPatch")
        if not isinstance(patch, dict):
            error("{} proposedPatch must be an object".format(label))
            continue
        analysis = patch.get("analysis")
        validate_analysis_object(analysis, label + " proposedPatch")

        source = patch.get("analysisSource")
        if not isinstance(source, dict):
            error("{} analysisSource must be an object".format(label))
        else:
            missing = SOURCE_FIELDS - set(source)
            extra = set(source) - SOURCE_FIELDS
            if missing:
                error("{} analysisSource missing {}".format(label, sorted(missing)))
            if extra:
                error("{} analysisSource has extras {}".format(label, sorted(extra)))
            if source.get("type") != "historical_chat_recovery":
                error("{} analysisSource.type is invalid".format(label))
            for key in ("sessionId", "messageId"):
                if not isinstance(source.get(key), str) or not UUID.match(
                    source.get(key, "")
                ):
                    error("{} analysisSource.{} is not a UUID".format(label, key))
            timestamp = source.get("timestamp")
            try:
                datetime.datetime.fromisoformat(
                    str(timestamp).replace("Z", "+00:00")
                )
            except ValueError:
                error("{} analysisSource.timestamp is invalid".format(label))
            if not isinstance(source.get("sourceTitle"), str) or not source.get(
                "sourceTitle", ""
            ).strip():
                error("{} analysisSource.sourceTitle is empty".format(label))
            if source.get("sourceFormat") != source_format:
                error("{} analysisSource.sourceFormat is inconsistent".format(label))
            if source.get("mappingVersion") != "2026-10-26.v2.1":
                error("{} mappingVersion is unexpected".format(label))
            if source.get("originalArtifact") != original_rel:
                error("{} analysisSource.originalArtifact is inconsistent".format(label))
            original_hash = source.get("originalSha256")
            if not isinstance(original_hash, str) or not SHA256.match(original_hash):
                error("{} originalSha256 is not a lowercase SHA-256".format(label))
            elif os.path.isfile(original_path):
                actual_hash = sha256(original_path)
                if actual_hash != original_hash:
                    error(
                        "{} original hash mismatch: expected {}, got {}".format(
                            label, original_hash, actual_hash
                        )
                    )
                source_title = source.get("sourceTitle")
                if isinstance(source_title, str) and source_title.strip():
                    with open(
                        original_path, encoding="utf-8", errors="replace"
                    ) as handle:
                        original_text = handle.read()
                    if source_title not in original_text:
                        error(
                            "{} sourceTitle does not appear in the original "
                            "artifact".format(label)
                        )

        proposed_echoes = patch.get("echoes")
        if proposed_echoes is not None:
            if not isinstance(proposed_echoes, dict):
                error("{} proposedPatch.echoes must be an object".format(label))
            else:
                if set(proposed_echoes) != {"candidates", "confirmed"}:
                    error(
                        "{} proposedPatch.echoes must contain candidates and "
                        "confirmed only".format(label)
                    )
                for key in ("candidates", "confirmed"):
                    value = proposed_echoes.get(key)
                    if not isinstance(value, list) or not all(
                        isinstance(item, str) and item.strip() for item in value
                    ):
                        error(
                            "{} proposedPatch.echoes.{} must be a string "
                            "array".format(label, key)
                        )

        entry = next(
            (item for item in entries if item.get("id") == entry_id), None
        )
        if entry is None:
            error("{} Archive entry does not exist".format(label))
            continue
        current_core = {
            key: value
            for key, value in entry.items()
            if key not in {"analysis", "analysisSource"}
        }
        snapshot_rel = sample.get("beforeSnapshot")
        if snapshot_rel is not None:
            if not isinstance(snapshot_rel, str) or not snapshot_rel:
                error("{} beforeSnapshot must be a non-empty path".format(label))
            else:
                snapshot_path = os.path.join(ROOT, snapshot_rel)
                if not os.path.isfile(snapshot_path):
                    error(
                        "{} beforeSnapshot does not exist: {}".format(
                            label, snapshot_rel
                        )
                    )
                else:
                    try:
                        snapshot = load_json(snapshot_path)
                    except (OSError, json.JSONDecodeError) as exc:
                        error(
                            "{} cannot parse beforeSnapshot: {}".format(label, exc)
                        )
                    else:
                        if snapshot.get("schemaVersion") != 1:
                            error(
                                "{} beforeSnapshot schemaVersion must be 1".format(
                                    label
                                )
                            )
                        if snapshot.get("entryId") != entry_id:
                            error(
                                "{} beforeSnapshot entryId does not match".format(
                                    label
                                )
                            )
                        if (
                            sample.get("metadataRevision") is None
                            and snapshot.get("entry") != current_core
                        ):
                            error(
                                "{} beforeSnapshot entry does not match current "
                                "entry outside analysis fields".format(label)
                            )
                        snapshot_image = snapshot.get("entry", {}).get("image")
                        snapshot_image_path = (
                            os.path.join(ROOT, snapshot_image)
                            if isinstance(snapshot_image, str)
                            else ""
                        )
                        if not os.path.isfile(snapshot_image_path):
                            error(
                                "{} beforeSnapshot image does not exist".format(label)
                            )
                        elif snapshot.get("imageSha256") != sha256(
                            snapshot_image_path
                        ):
                            error(
                                "{} beforeSnapshot imageSha256 does not match".format(
                                    label
                                )
                            )
        metadata_revision_rel = sample.get("metadataRevision")
        if metadata_revision_rel is not None:
            if (
                not isinstance(metadata_revision_rel, str)
                or not metadata_revision_rel
            ):
                error("{} metadataRevision must be a non-empty path".format(label))
            elif not isinstance(snapshot_rel, str) or not snapshot_rel:
                error("{} metadataRevision requires beforeSnapshot".format(label))
            else:
                revision_path = os.path.join(ROOT, metadata_revision_rel)
                snapshot_path = os.path.join(ROOT, snapshot_rel)
                if not os.path.isfile(revision_path):
                    error(
                        "{} metadataRevision does not exist: {}".format(
                            label, metadata_revision_rel
                        )
                    )
                elif not os.path.isfile(snapshot_path):
                    error(
                        "{} metadataRevision snapshot does not exist".format(label)
                    )
                else:
                    try:
                        revision = load_json(revision_path)
                        snapshot = load_json(snapshot_path)
                    except (OSError, json.JSONDecodeError) as exc:
                        error(
                            "{} cannot parse metadataRevision data: {}".format(
                                label, exc
                            )
                        )
                    else:
                        if revision.get("schemaVersion") != 1:
                            error(
                                "{} metadataRevision schemaVersion must be 1".format(
                                    label
                                )
                            )
                        if revision.get("entryId") != entry_id:
                            error(
                                "{} metadataRevision entryId does not match".format(
                                    label
                                )
                            )
                        try:
                            datetime.date.fromisoformat(
                                str(revision.get("approvedAt"))
                            )
                        except ValueError:
                            error(
                                "{} metadataRevision approvedAt must be "
                                "YYYY-MM-DD".format(label)
                            )
                        before = revision.get("before")
                        after = revision.get("after")
                        changes = revision.get("changes")
                        if before != snapshot.get("entry"):
                            error(
                                "{} metadataRevision before does not match "
                                "beforeSnapshot".format(label)
                            )
                        if after != current_core:
                            error(
                                "{} metadataRevision after does not match current "
                                "entry outside analysis fields".format(label)
                            )
                        if not isinstance(changes, dict) or not changes:
                            error(
                                "{} metadataRevision changes must be a non-empty "
                                "object".format(label)
                            )
                        elif isinstance(before, dict) and isinstance(after, dict):
                            changed_fields = {
                                key
                                for key in set(before) | set(after)
                                if before.get(key) != after.get(key)
                            }
                            if set(changes) != changed_fields:
                                error(
                                    "{} metadataRevision changes do not match "
                                    "the recorded entry difference".format(label)
                                )
                            for field, change in changes.items():
                                if not isinstance(change, dict):
                                    error(
                                        "{} metadataRevision change for {} must "
                                        "be an object".format(label, field)
                                    )
                                    continue
                                if (
                                    change.get("from") != before.get(field)
                                    or change.get("to") != after.get(field)
                                ):
                                    error(
                                        "{} metadataRevision change for {} does "
                                        "not match before/after".format(
                                            label, field
                                        )
                                    )
        if "analysis" in entry:
            expected_analysis = applied_reanalysis_analysis.get(
                entry_id, patch.get("analysis")
            )
            if entry.get("analysis") != expected_analysis:
                if entry_id in applied_reanalysis_analysis:
                    error(
                        "{} Archive analysis does not match applied "
                        "reanalysis".format(label)
                    )
                else:
                    error(
                        "{} Archive analysis does not match normalized "
                        "draft".format(label)
                    )
            if entry.get("analysisSource") != source:
                error(
                    "{} Archive analysisSource does not match normalized draft".format(
                        label
                    )
                )
            if proposed_echoes is not None and entry.get("echoes") != proposed_echoes:
                error("{} Archive echoes do not match proposedPatch".format(label))
            if archive_status == "pending":
                warn(
                    "{} is still marked pending although matching analysis is "
                    "already present".format(label)
                )
        elif archive_status == "imported":
            error("{} is marked imported but has no analysis".format(label))
        source_title = source.get("sourceTitle") if isinstance(source, dict) else None
        mapping_notes = normalized.get("mappingNotes")
        if (
            isinstance(source_title, str)
            and source_title != entry.get("title")
            and (
                not isinstance(mapping_notes, list)
                or not any(
                    isinstance(note, str) and source_title in note
                    for note in mapping_notes
                )
            )
        ):
            error(
                "{} sourceTitle differs from current title but mappingNotes "
                "does not explain the alias".format(label)
            )
        references = normalized.get("entryReferences")
        if not isinstance(references, dict):
            error("{} entryReferences must be an object".format(label))
            continue
        for field in ("image", "title", "category", "accent"):
            if references.get(field) != entry.get(field):
                error(
                    "{} entryReferences.{} does not match Archive".format(
                        label, field
                    )
                )
        image_rel = references.get("image")
        image_path = os.path.join(ROOT, image_rel) if isinstance(image_rel, str) else ""
        if not os.path.isfile(image_path):
            error("{} referenced image does not exist".format(label))
        elif references.get("imageSha256") != sha256(image_path):
            error("{} imageSha256 does not match the file".format(label))

        proposed_echoes = references.get("echoes")
        if "echoes" in entry:
            if proposed_echoes != entry.get("echoes"):
                error("{} entryReferences.echoes does not match Archive".format(label))
        elif proposed_echoes != {"candidates": [], "confirmed": []}:
            error(
                "{} missing Archive echoes must be represented as empty arrays in "
                "entryReferences".format(
                    label
                )
            )
        else:
            warn(
                "{} currently has no echoes; entryReferences uses empty arrays "
                "and any restoration is isolated in proposedPatch.echoes".format(label)
            )

        pending = normalized.get("pending")
        if not isinstance(pending, list) or not all(
            isinstance(item, str) and item.strip() for item in pending
        ):
            error("{} pending must be an array of strings".format(label))
        if status == "ready_for_review" and pending:
            error("{} ready_for_review cannot still have pending items".format(label))
        if status == "needs_owner_confirmation" and not pending:
            error(
                "{} needs_owner_confirmation must list the unresolved items".format(
                    label
                )
            )

    if errors:
        print("FAILED: {} error(s), {} warning(s)".format(len(errors), len(warnings)))
        for message in errors:
            print("ERROR:", message)
        for message in warnings:
            print("WARN:", message)
        return 1

    print(
        "OK: {} recovery sample(s), {} reanalysis record(s), {} warning(s)".format(
            len(samples), len(reanalyses), len(warnings)
        )
    )
    for message in warnings:
        print("WARN:", message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
