#!/usr/bin/env python3
"""Validate an approved GitHub issue and import it into Ayou-Lab."""

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

from candidate_common import (
    DATA_PATH,
    IMAGES_DIR,
    ROOT,
    CandidateError,
    append_entry,
    build_entry,
    decode_candidate_block,
    fetch_image,
    github_api,
    hamming_distance,
    inspect_image_bytes,
    load_entries,
    nearest_archive_matches,
    save_jpeg_bytes,
    sha256_bytes,
    slugify,
    today_shanghai,
    verify_current_rights,
)


LABEL_APPROVED = "ayou-approved"
LABEL_CANDIDATE = "ayou-candidate"
LABEL_IMPORTED = "ayou-imported"
LABEL_ATTENTION = "ayou-needs-attention"


def load_event(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def issue_labels(issue):
    return {
        label.get("name")
        for label in issue.get("labels", [])
        if isinstance(label, dict)
    }


def validated_event(event):
    if event.get("action") != "labeled":
        raise CandidateError("Workflow event is not an issue-label event")
    if (event.get("label") or {}).get("name") != LABEL_APPROVED:
        raise CandidateError("Workflow event is not for the approval label")
    issue = event.get("issue")
    if not isinstance(issue, dict):
        raise CandidateError("Workflow event has no issue")
    repo_owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "").strip()
    sender = (event.get("sender") or {}).get("login", "")
    if repo_owner and sender != repo_owner:
        raise CandidateError("Only the repository owner may approve a candidate")
    labels = issue_labels(issue)
    if LABEL_CANDIDATE not in labels:
        raise CandidateError("Issue is not an Ayou-Lab candidate")
    candidate = decode_candidate_block(issue.get("body", ""))
    return issue, candidate


def ensure_unique(candidate, entries):
    title_key = candidate["title"].casefold()
    for entry in entries:
        if str(entry.get("title", "")).casefold() == title_key:
            raise CandidateError("Candidate title already exists in the archive")
    candidate_id = slugify(candidate["title"])
    if any(entry.get("id") == candidate_id for entry in entries):
        raise CandidateError("Candidate id already exists in the archive")
    return candidate_id


def download_and_validate(candidate):
    source = candidate["source"]
    original = fetch_image(source["imageUrl"], source["provider"])
    metrics = inspect_image_bytes(original)
    if sha256_bytes(original) != candidate["image"]["sha256"]:
        distance = hamming_distance(
            candidate["fingerprint"], metrics["fingerprint"]
        )
        if distance > 4:
            raise CandidateError(
                "Source image changed after approval (visual distance {})".format(
                    distance
                )
            )
        # A provider may re-encode an unchanged thumbnail.
        print(
            "NOTICE: source image bytes changed but visual content still matches",
            file=sys.stderr,
        )
    nearest = nearest_archive_matches(metrics["fingerprint"])
    if nearest and nearest[0]["distance"] <= 12:
        raise CandidateError(
            "Approved image is a perceptual duplicate of {} (distance {})".format(
                nearest[0]["image"], nearest[0]["distance"]
            )
        )
    final_bytes = save_jpeg_bytes(original)
    final_metrics = inspect_image_bytes(final_bytes)
    return final_bytes, final_metrics, nearest


def run_archive_check():
    subprocess.run(
        [sys.executable, "scripts/check_archive.py", "--strict-analysis"],
        check=True,
    )


def prepare(event_path, result_path):
    event = load_event(event_path)
    issue, candidate = validated_event(event)
    rights_evidence = verify_current_rights(candidate)
    candidate = copy.deepcopy(candidate)
    candidate["source"]["licenseEvidence"] = rights_evidence
    entries = load_entries(DATA_PATH)
    candidate_id = ensure_unique(candidate, entries)
    final_bytes, metrics, nearest = download_and_validate(candidate)

    image_path = "images/{}.jpg".format(candidate_id)
    target = ROOT / image_path
    if target.exists():
        raise CandidateError("Target image path already exists: {}".format(image_path))

    entry = build_entry(
        candidate,
        image_path=image_path,
        accent=metrics["accent"],
        imported_at=today_shanghai(),
        issue_number=issue["number"],
    )
    entry["provenance"]["finalSha256"] = metrics["sha256"]
    entry["provenance"]["finalDimensions"] = "{}x{}".format(
        metrics["width"], metrics["height"]
    )

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    original_data = DATA_PATH.read_bytes()
    target.write_bytes(final_bytes)
    try:
        append_entry(DATA_PATH, entry)
        run_archive_check()
    except Exception:
        DATA_PATH.write_bytes(original_data)
        target.unlink(missing_ok=True)
        raise

    result = {
        "schemaVersion": 1,
        "issueNumber": issue["number"],
        "issueTitle": issue.get("title", ""),
        "candidateTitle": candidate["title"],
        "category": candidate["category"],
        "id": candidate_id,
        "imagePath": image_path,
        "nearestArchive": nearest,
    }
    with Path(result_path).open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def pr_body(result):
    return """
Imports the owner-approved visual candidate from issue #{issue}.

- Entry: `{id}`
- Visual DNA: `{category}`
- Image: `{image}`
- Source rights: public domain or CC0, verified by the candidate workflow

The import workflow has already:

1. Re-fetched and decoded the source image.
2. Compared its content-cropped perceptual hash with the archive.
3. Checked id, title, image path, JSON structure, and analysis fields.
4. Re-measured the accent from the final JPEG.

Review the source and visual judgement before merging.

Closes #{issue}
""".format(
        issue=result["issueNumber"],
        id=result["id"],
        category=result["category"],
        image=result["imagePath"],
    ).strip()


def post_pr(event_path, result_path):
    event = load_event(event_path)
    issue = event.get("issue") or {}
    issue_number = issue.get("number")
    if not issue_number:
        raise CandidateError("Workflow event has no issue number")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    branch = os.environ.get("CANDIDATE_BRANCH", "").strip()
    if not token or not repo or not branch:
        raise CandidateError(
            "GITHUB_TOKEN, GITHUB_REPOSITORY and CANDIDATE_BRANCH are required"
        )
    with Path(result_path).open(encoding="utf-8") as handle:
        result = json.load(handle)
    result["issueNumber"] = issue_number
    payload = {
        "title": "Import approved candidate: {}".format(result["candidateTitle"]),
        "head": branch,
        "base": os.environ.get("GITHUB_BASE_BRANCH", "main"),
        "body": pr_body(result),
    }
    pull = github_api(
        "POST",
        "/repos/{}/pulls".format(repo),
        token=token,
        payload=payload,
    )
    github_api(
        "POST",
        "/repos/{}/issues/{}/comments".format(repo, issue_number),
        token=token,
        payload={
            "body": (
                "Candidate validated and opened as pull request #{pr}.\n\n"
                "The archive will change only after this PR is merged.\n\n{pull}"
            ).format(
                pr=pull["number"],
                pull=pull["html_url"],
            )
        },
    )
    github_api(
        "POST",
        "/repos/{}/issues/{}/labels".format(repo, issue_number),
        token=token,
        payload={"labels": [LABEL_IMPORTED]},
    )
    print(pull["html_url"])
    return pull


def main():
    parser = argparse.ArgumentParser(
        description="Import one approved Ayou-Lab candidate safely."
    )
    parser.add_argument(
        "--event-path",
        default=os.environ.get("GITHUB_EVENT_PATH", ""),
        help="GitHub Actions event JSON",
    )
    parser.add_argument(
        "--result-path",
        default="/tmp/ayou-candidate-import.json",
        help="Where to save the import result",
    )
    parser.add_argument(
        "--post-pr",
        action="store_true",
        help="After pushing the branch, open the pull request and update the issue",
    )
    args = parser.parse_args()
    if not args.event_path:
        raise SystemExit("--event-path or GITHUB_EVENT_PATH is required")
    try:
        if args.post_pr:
            post_pr(args.event_path, args.result_path)
        else:
            prepare(args.event_path, args.result_path)
    except CandidateError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
