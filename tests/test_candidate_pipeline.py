import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from candidate_common import (  # noqa: E402
    ANALYSIS_FIELDS,
    CandidateError,
    append_entry,
    build_entry,
    decode_candidate_block,
    encode_candidate_block,
    hamming_distance,
    inspect_image_bytes,
    nearest_archive_matches,
    save_jpeg_bytes,
    slugify,
    validate_candidate,
    verify_current_rights,
    wikimedia_license_allowed,
)
from generate_candidates import issue_body  # noqa: E402


def sample_candidate():
    analysis = {
        field: "画面中可见的具体视觉证据，并保留必要的观察限制。"
        for field in ANALYSIS_FIELDS
    }
    return {
        "schemaVersion": 1,
        "generatedAt": "2026-10-29T00:17:00+00:00",
        "sourceKey": "aic:1",
        "title": "Quiet Red Field",
        "fitScore": 88,
        "fitReason": "The restrained color field and quiet imbalance fit the archive.",
        "category": "color",
        "medium": "painting",
        "note": "A broad red field holds one small pale form at its edge.",
        "tags": ["red", "field", "minimal"],
        "echoes": {
            "candidates": ["A quiet evening light"],
            "confirmed": [],
        },
        "analysis": analysis,
        "accent": "#B34D35",
        "fingerprint": "0123456789abcdef",
        "image": {
            "width": 1686,
            "height": 1200,
            "sha256": "a" * 64,
        },
        "nearestArchive": [],
        "source": {
            "provider": "aic",
            "providerName": "Art Institute of Chicago",
            "sourceId": "1",
            "title": "Red Field",
            "author": "Example Artist",
            "date": "1901",
            "mediumText": "Oil on canvas",
            "pageUrl": "https://www.artic.edu/artworks/1",
            "imageUrl": (
                "https://www.artic.edu/iiif/2/example/full/1686,/0/default.jpg"
            ),
            "license": "Public domain",
            "licenseUrl": "https://www.artic.edu/terms",
            "rightsStatus": "public_domain",
            "licenseEvidence": "The public API reports is_public_domain=true.",
        },
    }


class CandidatePipelineTests(unittest.TestCase):
    def test_candidate_round_trip(self):
        candidate = sample_candidate()
        validate_candidate(candidate)
        decoded = decode_candidate_block(encode_candidate_block(candidate))
        self.assertEqual(decoded["sourceKey"], "aic:1")
        self.assertEqual(decoded["echoes"]["confirmed"], [])

    def test_confirmed_echo_is_rejected_before_approval(self):
        candidate = sample_candidate()
        candidate["echoes"]["confirmed"] = ["A personal memory"]
        with self.assertRaises(CandidateError):
            validate_candidate(candidate)

    def test_non_public_domain_candidate_is_rejected(self):
        candidate = sample_candidate()
        candidate["source"]["rightsStatus"] = "copyrighted"
        with self.assertRaises(CandidateError):
            validate_candidate(candidate)

    @patch("candidate_common.http_json")
    def test_approval_rechecks_aic_public_domain_status(self, http_json):
        candidate = sample_candidate()
        http_json.return_value = {
            "data": {
                "id": 1,
                "is_public_domain": True,
                "image_id": "example",
            }
        }
        evidence = verify_current_rights(candidate)
        self.assertIn("reported is_public_domain=true", evidence)

    def test_wikimedia_rights_requires_public_domain_or_cc0(self):
        cc0 = {
            "LicenseShortName": {"value": "CC0 1.0"},
            "License": {"value": "cc0"},
        }
        copyrighted = {
            "LicenseShortName": {"value": "CC BY-SA 4.0"},
            "License": {"value": "cc-by-sa"},
        }
        self.assertEqual(wikimedia_license_allowed(cc0), "cc0")
        self.assertIsNone(wikimedia_license_allowed(copyrighted))

    def test_slugify_is_stable(self):
        self.assertEqual(slugify("Quiet Red Field"), "quiet-red-field")
        self.assertEqual(slugify("  "), "untitled")

    def test_append_entry_preserves_existing_prefix(self):
        existing = [
            {
                "id": "first",
                "title": "First",
                "date": "2026-01-01",
                "source": "collected",
                "medium": "photo",
                "category": "nature",
                "note": "An existing entry.",
                "image": "images/first.jpg",
                "accent": "#123456",
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "entries.json"
            original = json.dumps(existing, ensure_ascii=False, indent=2) + "\n"
            path.write_text(original, encoding="utf-8")
            append_entry(path, {"id": "second", "title": "Second"})
            updated = path.read_text(encoding="utf-8")
            original_prefix = original[: original.rfind("]")].rstrip()
            self.assertTrue(updated.startswith(original_prefix))
            self.assertEqual(len(json.loads(updated)), 2)

    def test_entry_builder_keeps_confirmed_echoes_empty(self):
        entry = build_entry(
            sample_candidate(),
            image_path="images/quiet-red-field.jpg",
            accent="#B34D35",
            imported_at="2026-10-29",
            issue_number=42,
        )
        self.assertEqual(entry["id"], "quiet-red-field")
        self.assertEqual(entry["echoes"]["confirmed"], [])
        self.assertEqual(entry["provenance"]["rightsStatus"], "public_domain")
        self.assertEqual(entry["candidateIssue"], 42)

    def test_issue_body_contains_review_instructions_and_hidden_record(self):
        body = issue_body(sample_candidate(), "Approve or reject this candidate.")
        self.assertIn("![Candidate]", body)
        self.assertIn("ayou-approved", body)
        self.assertIn("<!-- AYOU_CANDIDATE_V1", body)

    def test_image_fingerprint_and_accent_are_measurable(self):
        sample = next((ROOT / "images").glob("*.jpg"))
        data = sample.read_bytes()
        metrics = inspect_image_bytes(data)
        self.assertGreater(metrics["width"], 0)
        self.assertGreater(metrics["height"], 0)
        self.assertRegex(metrics["fingerprint"], r"^[0-9a-f]{16}$")
        self.assertRegex(metrics["accent"], r"^#[0-9A-F]{6}$")
        self.assertEqual(hamming_distance(metrics["fingerprint"], metrics["fingerprint"]), 0)

    def test_current_archive_image_matches_itself(self):
        sample = next((ROOT / "images").glob("*.jpg"))
        metrics = inspect_image_bytes(sample.read_bytes())
        matches = nearest_archive_matches(metrics["fingerprint"])
        self.assertEqual(matches[0]["image"], str(sample.relative_to(ROOT)))
        self.assertEqual(matches[0]["distance"], 0)

    def test_jpeg_conversion_returns_decodable_image(self):
        sample = next((ROOT / "images").glob("*.jpg"))
        converted = save_jpeg_bytes(sample.read_bytes(), max_edge=400)
        metrics = inspect_image_bytes(converted)
        self.assertLessEqual(max(metrics["width"], metrics["height"]), 400)


if __name__ == "__main__":
    unittest.main()
