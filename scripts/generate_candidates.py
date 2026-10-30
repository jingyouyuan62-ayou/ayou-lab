#!/usr/bin/env python3
"""Find and analyze three public-domain visual candidates per daily run."""

import argparse
import base64
import datetime as dt
import json
import os
import random
import re
import sys
from urllib.parse import urlencode

from candidate_common import (
    ANALYSIS_FIELDS,
    CATEGORIES,
    CandidateError,
    SPEC_PATH,
    WIKIMEDIA_API,
    clean_html,
    decode_candidate_block,
    encode_candidate_block,
    fetch_image,
    github_api,
    http_json,
    inspect_image_bytes,
    markdown_escape,
    nearest_archive_matches,
    normalize_https_url,
    save_jpeg_bytes,
    today_shanghai,
    validate_candidate,
    wikimedia_license_allowed,
)


AIC_API = "https://api.artic.edu/api/v1/artworks/search"
LABEL_CANDIDATE = "ayou-candidate"
LABEL_PENDING = "ayou-pending"

QUERY_BANK = {
    "nature": [
        "botanical garden",
        "forest landscape",
        "river landscape",
        "flowers still life",
        "cloud landscape",
        "tree branches",
    ],
    "memory": [
        "window interior",
        "old house",
        "street cafe",
        "domestic still life",
        "garden path",
        "kitchen table",
    ],
    "strange": [
        "surreal landscape",
        "masked figure",
        "convex mirror",
        "dream vision",
        "fragment collage",
        "uncanny object",
    ],
    "color": [
        "color field",
        "bold color print",
        "colorful textile",
        "graphic poster",
        "dramatic sunset",
        "ornamental pattern",
    ],
    "dream": [
        "moonlit landscape",
        "cloud study",
        "night sea",
        "dream landscape",
        "stars night",
        "mysterious atmosphere",
    ],
}


def run_id():
    return os.environ.get("GITHUB_RUN_ID") or dt.datetime.now().strftime("%Y%m%d%H%M%S")


def choose_categories(seed):
    categories = sorted(CATEGORIES)
    rng = random.Random("{}:{}".format(today_shanghai(), seed))
    return rng.sample(categories, 3)


def classify_medium(medium_text):
    text = (medium_text or "").lower()
    if "photograph" in text:
        return "photo"
    if "watercolor" in text or "drawing" in text or "illustration" in text:
        return "illustration"
    if "painting" in text:
        return "painting"
    if "print" in text or "woodcut" in text or "engraving" in text:
        return "print"
    if "textile" in text or "silk" in text or "embroidery" in text:
        return "textile"
    if "collage" in text:
        return "collage"
    return "mixed media"


def artic_search(query, limit=24):
    fields = (
        "id,title,image_id,is_public_domain,artist_display,"
        "date_display,medium_display,thumbnail"
    )
    params = urlencode(
        {
            "q": query,
            "limit": limit,
            "fields": fields,
        }
    )
    payload = http_json("{}?{}".format(AIC_API, params))
    for item in payload.get("data", []):
        if not item.get("is_public_domain") or not item.get("image_id"):
            continue
        title = clean_html(item.get("title"))
        if not title:
            continue
        image_id = item["image_id"]
        work_id = item["id"]
        yield {
            "sourceKey": "aic:{}".format(work_id),
            "source": {
                "provider": "aic",
                "providerName": "Art Institute of Chicago",
                "sourceId": str(work_id),
                "title": title,
                "author": clean_html(item.get("artist_display")) or "Unknown",
                "date": clean_html(item.get("date_display")) or "Date unknown",
                "mediumText": clean_html(item.get("medium_display")) or "Unknown medium",
                "pageUrl": "https://www.artic.edu/artworks/{}".format(work_id),
                "imageUrl": (
                    "https://www.artic.edu/iiif/2/{}/full/1686,/0/default.jpg"
                ).format(image_id),
                "license": "Public domain",
                "licenseUrl": "https://www.artic.edu/terms",
                "rightsStatus": "public_domain",
                "licenseEvidence": (
                    "The Art Institute of Chicago public API reports "
                    "is_public_domain=true for this artwork."
                ),
            },
            "searchTerm": query,
            "medium": classify_medium(item.get("medium_display")),
        }


def wikimedia_search(query, limit=16):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": "filetype:bitmap {}".format(query),
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": "1280",
        "format": "json",
        "formatversion": "2",
    }
    payload = http_json("{}?{}".format(WIKIMEDIA_API, urlencode(params)))
    pages = sorted(
        payload.get("query", {}).get("pages", []),
        key=lambda page: page.get("index", 999999),
    )
    for page in pages:
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        metadata = info.get("extmetadata") or {}
        rights_status = wikimedia_license_allowed(metadata)
        if rights_status is None:
            continue
        title = clean_html(metadata.get("ObjectName", {}).get("value"))
        if not title:
            title = clean_html(page.get("title", "").removeprefix("File:"))
        author = clean_html(metadata.get("Artist", {}).get("value")) or "Unknown"
        source_date = (
            clean_html(metadata.get("DateTimeOriginal", {}).get("value"))
            or "Date unknown"
        )
        license_name = (
            clean_html(metadata.get("LicenseShortName", {}).get("value"))
            or clean_html(metadata.get("UsageTerms", {}).get("value"))
            or rights_status.replace("_", " ").title()
        )
        license_url = normalize_https_url(
            clean_html(metadata.get("LicenseUrl", {}).get("value"))
            or "https://commons.wikimedia.org/wiki/Commons:Licensing"
        )
        image_url = normalize_https_url(info.get("thumburl") or info.get("url"))
        page_url = normalize_https_url(info.get("descriptionurl"))
        if not title or not image_url or not page_url:
            continue
        yield {
            "sourceKey": "wikimedia:{}".format(page.get("pageid")),
            "source": {
                "provider": "wikimedia",
                "providerName": "Wikimedia Commons",
                "sourceId": str(page.get("pageid")),
                "title": title,
                "author": author,
                "date": source_date,
                "mediumText": "Digital image",
                "pageUrl": page_url,
                "imageUrl": image_url,
                "license": license_name,
                "licenseUrl": license_url,
                "rightsStatus": rights_status,
                "licenseEvidence": (
                    "Wikimedia Commons metadata identifies the file as {}."
                ).format(license_name),
            },
            "searchTerm": query,
            "medium": "photo",
        }


def existing_candidate_source_keys(repo, token):
    seen = set()
    for page in range(1, 6):
        path = (
            "/repos/{}/issues?state=all&labels={}&per_page=100&page={}"
        ).format(repo, LABEL_CANDIDATE, page)
        issues = github_api("GET", path, token=token) or []
        for issue in issues:
            try:
                candidate = decode_candidate_block(issue.get("body", ""))
            except CandidateError:
                continue
            seen.add(candidate["sourceKey"])
        if len(issues) < 100:
            break
    return seen


def deepseek_analysis(candidate, image_bytes, api_key, base_url, model):
    spec = SPEC_PATH.read_text(encoding="utf-8")
    required_json = {
        "title": "1-5 plain English words",
        "fitScore": "integer 0-100 for fit with the current Visual DNA",
        "fitReason": "one concise sentence explaining the score",
        "category": "exactly one of: {}".format(", ".join(sorted(CATEGORIES))),
        "medium": "short medium label",
        "note": "one factual English sentence",
        "tags": ["2-8 short kebab-case tags"],
        "echoes": {
            "candidates": ["optional AI-association strings"],
            "confirmed": [],
        },
        "analysis": {field: "Chinese observation-first prose" for field in ANALYSIS_FIELDS},
    }
    prompt = """
You are the daily candidate analyst for Ayou-Lab.

Read the image and its authoritative source metadata. Return only one JSON object.
Do not use Markdown fences. Do not add fields outside the requested schema.

The project records visual material the owner likes for intuitive reasons.
Observe first, interpret second. Never invent an exact place, event, identity,
camera, material, or textual content that the image does not show. If uncertain,
say what cannot be confirmed in `analysis.uncertainty`.

The working Visual DNA is NATURE, MEMORY, STRANGE, COLOR, DREAM. Choose one
best-fitting category. If none fit, still choose the least misleading one and
state the limitation in `analysis.dna`; never force a false claim.

`title` must be 1-5 plain English words derived from visible form, not a copy of
the museum catalogue title where possible. `note` must be one English sentence.
`echoes.confirmed` must always be an empty array. `echoes.candidates` are only
AI suggestions. The measured accent is supplied below; refer to that exact hex
inside `analysis.color` and do not infer a different official accent.

Required object shape:
{}

Project analysis specification:
{}
""".format(
        json.dumps(required_json, ensure_ascii=False, indent=2),
        spec,
    )
    source = candidate["source"]
    analysis_image = save_jpeg_bytes(image_bytes, max_edge=1600, quality=90)
    image_data_url = "data:image/jpeg;base64,{}".format(
        base64.b64encode(analysis_image).decode("ascii")
    )
    user_text = """
Candidate source metadata:
- provider: {provider}
- catalogue title: {title}
- creator: {author}
- date: {date}
- medium: {medium}
- source page: {page}
- measured image accent: {accent}

Analyze only this one image. The result will be held for the owner's approval.
""".format(
        provider=source["providerName"],
        title=source["title"],
        author=source["author"],
        date=source["date"],
        medium=source["mediumText"],
        page=source["pageUrl"],
        accent=candidate["accent"],
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url,
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.35,
        "max_tokens": 4200,
    }
    endpoint = "{}/chat/completions".format(base_url.rstrip("/"))
    response = http_json(
        endpoint,
        method="POST",
        headers={
            "Authorization": "Bearer {}".format(api_key),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        body=json.dumps(payload).encode("utf-8"),
        timeout=180,
        max_bytes=10 * 1024 * 1024,
    )
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise CandidateError("DeepSeek returned an unexpected response") from exc
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise CandidateError("DeepSeek did not return valid JSON") from exc
    if not isinstance(result, dict):
        raise CandidateError("DeepSeek response must be one JSON object")
    return result


def candidate_from_source(source_candidate, api_key, base_url, model):
    image_bytes = fetch_image(
        source_candidate["source"]["imageUrl"],
        source_candidate["source"]["provider"],
    )
    metrics = inspect_image_bytes(image_bytes)
    nearest = nearest_archive_matches(metrics["fingerprint"])
    if nearest and nearest[0]["distance"] <= 12:
        raise CandidateError(
            "Perceptual duplicate of {} (distance {})".format(
                nearest[0]["image"], nearest[0]["distance"]
            )
        )

    candidate = {
        "schemaVersion": 1,
        "generatedAt": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "sourceKey": source_candidate["sourceKey"],
        "source": source_candidate["source"],
        "medium": source_candidate["medium"],
        "searchTerm": source_candidate["searchTerm"],
        "accent": metrics["accent"],
        "fingerprint": metrics["fingerprint"],
        "image": {
            "width": metrics["width"],
            "height": metrics["height"],
            "sha256": metrics["sha256"],
        },
        "nearestArchive": nearest,
    }
    analysis = deepseek_analysis(
        candidate, image_bytes, api_key, base_url, model
    )
    echoes = analysis.get("echoes")
    if not isinstance(echoes, dict):
        echoes = {"candidates": [], "confirmed": []}
    candidate.update(
        {
            "title": analysis.get("title"),
            "fitScore": analysis.get("fitScore"),
            "fitReason": analysis.get("fitReason"),
            "category": analysis.get("category"),
            "medium": analysis.get("medium") or source_candidate["medium"],
            "note": analysis.get("note"),
            "tags": analysis.get("tags"),
            "echoes": echoes,
            "analysis": analysis.get("analysis"),
        }
    )
    candidate["echoes"]["confirmed"] = []
    validate_candidate(candidate)
    if candidate["fitScore"] < 65:
        raise CandidateError(
            "Visual DNA fit score {} is below the 65 threshold".format(
                candidate["fitScore"]
            )
        )
    return candidate


def issue_body(candidate, issue_instructions):
    source = candidate["source"]
    analysis = candidate["analysis"]
    nearest = candidate.get("nearestArchive") or []
    nearest_text = (
        ", ".join(
            "{} ({})".format(item["image"], item["distance"]) for item in nearest
        )
        if nearest
        else "No close archive match"
    )
    return """
## {title}

![Candidate]({image})

**Visual DNA:** `{category}`

**Visual DNA fit:** `{fit_score}/100` — {fit_reason}

**Suggested medium:** `{medium}`

**Measured accent:** `{accent}`

**Source:** [{source_title}]({source_page}) — {author}

**License evidence:** {license} ([terms]({license_url}))
**Nearest archive fingerprints:** {nearest}

> {note}

### Review

{instructions}

<details>
<summary>Complete AI analysis and provenance</summary>

#### Content

{content}

#### Composition

{composition}

#### Color

{color}

#### Typography

{typography}

#### Texture

{texture}

#### Material

{material}

#### Spatial depth

{spatial}

#### Hierarchy

{hierarchy}

#### Mood

{mood}

#### Visual style

{style}

#### Interaction

{interaction}

#### Visual DNA

{dna}

#### Echoes candidates

{echoes}

#### Uncertainty

{uncertainty}

#### Source record

- Provider: {provider}
- Source ID: `{source_id}`
- Catalogue date: {source_date}
- Rights status: `{rights_status}`
- Evidence: {evidence}
- Image URL: {image_url}

</details>

---

To approve, add the **`ayou-approved`** label. This creates a review branch and
pull request; it does not publish directly to `main`.

{block}
""".format(
        title=markdown_escape(candidate["title"]),
        image=markdown_escape(source["imageUrl"]),
        category=markdown_escape(candidate["category"].upper()),
        fit_score=candidate["fitScore"],
        fit_reason=markdown_escape(candidate["fitReason"]),
        medium=markdown_escape(candidate["medium"]),
        accent=candidate["accent"],
        source_title=markdown_escape(source["title"]),
        source_page=source["pageUrl"],
        author=markdown_escape(source["author"]),
        license=markdown_escape(source["license"]),
        license_url=source["licenseUrl"],
        nearest=markdown_escape(nearest_text),
        note=markdown_escape(candidate["note"]),
        instructions=issue_instructions,
        content=markdown_escape(analysis["content"]),
        composition=markdown_escape(analysis["composition"]),
        color=markdown_escape(analysis["color"]),
        typography=markdown_escape(analysis["typography"]),
        texture=markdown_escape(analysis["texture"]),
        material=markdown_escape(analysis["material"]),
        spatial=markdown_escape(analysis["spatialDepth"]),
        hierarchy=markdown_escape(analysis["hierarchy"]),
        mood=markdown_escape(analysis["mood"]),
        style=markdown_escape(analysis["visualStyle"]),
        interaction=markdown_escape(analysis["interaction"]),
        dna=markdown_escape(analysis["dna"]),
        echoes="\n".join(
            "- {}".format(markdown_escape(item))
            for item in candidate["echoes"]["candidates"]
        )
        or "None suggested.",
        uncertainty=markdown_escape(analysis["uncertainty"]),
        provider=markdown_escape(source["providerName"]),
        source_id=markdown_escape(source["sourceId"]),
        source_date=markdown_escape(source["date"]),
        rights_status=markdown_escape(source["rightsStatus"]),
        evidence=markdown_escape(source["licenseEvidence"]),
        image_url=markdown_escape(source["imageUrl"]),
        block=encode_candidate_block(candidate),
    ).strip()


def ensure_label(repo, token, name, color, description):
    try:
        github_api(
            "POST",
            "/repos/{}/labels".format(repo),
            token=token,
            payload={"name": name, "color": color, "description": description},
        )
    except CandidateError as exc:
        if "HTTP 422" not in str(exc):
            raise


def create_issue(repo, token, candidate):
    instructions = (
        "Check the image, source page, license evidence, and analysis. "
        "Approve with the `ayou-approved` label or reject with `ayou-rejected`."
    )
    body = issue_body(candidate, instructions)
    if len(body.encode("utf-8")) > 60000:
        raise CandidateError("Candidate Issue body would exceed GitHub's limit")
    issue = github_api(
        "POST",
        "/repos/{}/issues".format(repo),
        token=token,
        payload={
            "title": "[Candidate] {} · {}".format(
                candidate["title"], candidate["category"].upper()
            ),
            "body": body,
            "labels": [LABEL_CANDIDATE, LABEL_PENDING],
        },
    )
    return issue


def source_iter(category, attempt):
    query = QUERY_BANK[category][attempt % len(QUERY_BANK[category])]
    # AIC's image server currently returns Cloudflare 403 to GitHub-hosted
    # runners, so automatic discovery stays on Wikimedia until that changes.
    adapter_order = ["wikimedia"]
    for adapter in adapter_order:
        try:
            if adapter == "artic":
                yield from artic_search(query)
            else:
                yield from wikimedia_search(query)
        except CandidateError as exc:
            print("WARN: {} search failed: {}".format(adapter, exc), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Create three daily Ayou-Lab candidate review issues."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print validated candidates instead of creating GitHub issues.",
    )
    parser.add_argument("--seed", default=None)
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not configured")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not args.dry_run and (not token or not repo):
        raise SystemExit("GITHUB_TOKEN and GITHUB_REPOSITORY are required")

    seed = args.seed or run_id()
    seen = existing_candidate_source_keys(repo, token) if not args.dry_run else set()
    selected = []
    rejected_keys = set()

    for category_index, category in enumerate(choose_categories(seed)):
        found = None
        for attempt, source_candidate in enumerate(source_iter(category, category_index)):
            source_key = source_candidate["sourceKey"]
            if source_key in seen or source_key in rejected_keys:
                continue
            if attempt >= 12:
                break
            try:
                candidate = candidate_from_source(
                    source_candidate, api_key, base_url, model
                )
            except CandidateError as exc:
                rejected_keys.add(source_key)
                print(
                    "SKIP {}: {}".format(source_key, exc),
                    file=sys.stderr,
                )
                continue
            found = candidate
            seen.add(source_key)
            break
        if found is None:
            raise SystemExit(
                "Could not find a valid {} candidate; no batch was published".format(
                    category
                )
            )
        selected.append(found)

    if args.dry_run:
        print(json.dumps(selected, ensure_ascii=False, indent=2))
        return

    ensure_label(
        repo,
        token,
        LABEL_CANDIDATE,
        "705044",
        "Ayou-Lab daily visual candidate",
    )
    ensure_label(
        repo,
        token,
        LABEL_PENDING,
        "D8C6A3",
        "Candidate waiting for owner review",
    )
    ensure_label(
        repo,
        token,
        "ayou-approved",
        "2F6F4E",
        "Approve this candidate for a review pull request",
    )
    ensure_label(
        repo,
        token,
        "ayou-rejected",
        "9C3D32",
        "Rejected visual candidate",
    )
    ensure_label(
        repo,
        token,
        "ayou-imported",
        "2F5D8C",
        "Candidate converted into a pull request",
    )

    for candidate in selected:
        issue = create_issue(repo, token, candidate)
        print(
            "{} | {} | {}".format(
                candidate["category"].upper(),
                candidate["title"],
                issue["html_url"],
            )
        )


if __name__ == "__main__":
    main()
