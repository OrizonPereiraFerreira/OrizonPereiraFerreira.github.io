#!/usr/bin/env python3
"""Update js/data.js with journal articles found on OpenAlex (https://openalex.org).

OpenAlex indexes the same literature as Google Scholar but has an open API, so the
page can be refreshed automatically (Google Scholar blocks automated access).
The author is identified by ORCID.

What it does:
  * adds journal articles that are not on the page yet (matched by DOI and by title);
  * when an added article is the published version of an item in "Preprints",
    moves it (keeping its code/PDF links);
  * fills volume/pages of items marked "To appear" once they are published.

It never removes or rewrites anything else. Articles that must never be added
(e.g. wrongly attributed works) go in scripts/sync-ignore.txt, one DOI per line.

Usage:  python3 scripts/sync_publications.py [--dry-run]
"""
import datetime
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ORCID = "0000-0002-5758-0320"
ME = "O. P. Ferreira"
ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "js" / "data.js"
IGNORE_FILE = ROOT / "scripts" / "sync-ignore.txt"
JOURNALS = "Articles in journals"
PREPRINTS = "Preprints"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "academic-page-sync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def openalex_works():
    works, cursor = [], "*"
    while cursor:
        q = urllib.parse.urlencode({"filter": "author.orcid:" + ORCID, "per-page": 200, "cursor": cursor})
        page = fetch_json("https://api.openalex.org/works?" + q)
        works += page["results"]
        cursor = page["meta"].get("next_cursor") if page["results"] else None
    return works


def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def norm(s):
    s = unicodedata.normalize("NFKD", plain(html.unescape(s or ""))).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def doi_of(s):
    m = re.search(r"10\.\d{4,9}/[^\s\"'<>]+", s or "")
    return m.group(0).lower().rstrip(".") if m else ""


def initials(full_name):
    """'Jen-Chih Yao' -> 'J.-C. Yao'; 'Orizon Pereira Ferreira' -> 'O. P. Ferreira'."""
    parts = plain(full_name).replace(".", ". ").split()
    if len(parts) < 2:
        return full_name
    last = parts[-1]
    given = []
    for p in parts[:-1]:
        given.append("-".join(x[0].upper() + "." for x in p.split("-") if x))
    return " ".join(given + [last])


def ref_of(biblio):
    vol, issue = biblio.get("volume"), biblio.get("issue")
    first, last = biblio.get("first_page"), biblio.get("last_page")
    if not vol:
        return ""
    ref = vol + (f"({issue})" if issue else "")
    if first and last and first != last:
        ref += f", {first}–{last}"
    elif first:
        ref += f", {first}"
    return ref


def main():
    dry = "--dry-run" in sys.argv
    src = DATA_FILE.read_text(encoding="utf-8")
    i, j = src.index("{"), src.rindex("}") + 1
    data = json.loads(src[i:j])
    groups = {g["name"]: g for g in data["publications"]}
    journals, preprints = groups[JOURNALS]["items"], groups.get(PREPRINTS, {"items": []})["items"]

    ignore = set()
    if IGNORE_FILE.exists():
        ignore = {doi_of(l) for l in IGNORE_FILE.read_text().splitlines() if doi_of(l)}

    known_dois, known_titles = set(), set()
    for g in data["publications"]:
        for p in g["items"]:
            for f in ("url", "pdf", "venueUrl"):
                if doi_of(p.get(f)):
                    known_dois.add(doi_of(p.get(f)))
            if g["name"] != PREPRINTS:
                known_titles.add(norm(p["title"]))

    # Spellings already used on the page, so new entries look like the old ones
    author_forms = {}
    venue_forms = {}
    for g in data["publications"]:
        for p in g["items"]:
            for a in p["authors"]:
                author_forms.setdefault((norm(a.split()[-1]), a[0].upper()), a)
            if p.get("venue"):
                venue_forms.setdefault(norm(p["venue"]), (p["venue"], p.get("venueUrl", "")))

    def author_name(a):
        if a.get("author", {}).get("orcid", "").endswith(ORCID):
            return ME
        name = a.get("author", {}).get("display_name") or a.get("raw_author_name") or ""
        short = initials(name)
        return author_forms.get((norm(short.split()[-1]), short[0].upper()), short)

    works = openalex_works()
    changes = []
    added = []
    seen = set()

    for w in sorted(works, key=lambda w: (w.get("publication_date") or "")):
        src_ = (w.get("primary_location") or {}).get("source") or {}
        doi = doi_of(w.get("doi"))
        title = plain(w.get("title"))
        if w.get("type") != "article" or src_.get("type") != "journal" or not doi or not title:
            continue
        if doi in known_dois or doi in ignore or norm(title) in known_titles or norm(title) in seen:
            continue
        seen.add(norm(title))
        venue, venue_url = venue_forms.get(norm(src_.get("display_name")), (src_.get("display_name", ""), ""))
        ref = ref_of(w.get("biblio") or {})
        item = {
            "n": 0,
            "authors": [author_name(a) for a in w.get("authorships", [])],
            "title": html.escape(title, quote=False),
            "venue": venue,
            "ref": ref,
            "year": w.get("publication_year"),
            "url": "https://doi.org/" + doi,
            "pdf": "",
            "code": "",
        }
        if not ref:
            item["status"] = "To appear"
        if venue_url:
            item["venueUrl"] = venue_url
        # published version of a preprint: take its links and remove it from Preprints
        for pre in list(preprints):
            if norm(pre["title"]) == norm(title):
                item["code"] = pre.get("code", "") or item["code"]
                item["pdf"] = pre.get("pdf", "") or item["pdf"]
                preprints.remove(pre)
                changes.append("moved from Preprints: " + title)
        added.append(item)
        changes.append(f"added: {title} ({venue}, {item['year']})")

    # Place it in its year. If the numbering of that year has a free number, use it;
    # otherwise put it at the top of the year and shift up the numbers above it.
    for item in sorted(added, key=lambda p: p["year"] or 0):
        y = item["year"] or 0
        pos = next((k for k, p in enumerate(journals) if (p.get("year") or 0) <= y), len(journals))
        gap = None
        for k in range(pos, len(journals)):
            a = journals[k]
            if (a.get("year") or 0) != y:
                break
            b = journals[k + 1] if k + 1 < len(journals) else None
            if a.get("n") and a["n"] - ((b or {}).get("n") or 0) > 1:
                gap = k + 1
                break
        if gap is not None:
            item["n"] = journals[gap - 1]["n"] - 1
            journals.insert(gap, item)
            continue
        below = next((p.get("n") for p in journals[pos:] if p.get("n")), 0)
        item["n"] = below + 1
        if any(p.get("n") == item["n"] for p in journals):
            for p in journals:
                if (p.get("n") or 0) >= item["n"]:
                    p["n"] += 1
        journals.insert(pos, item)

    # "To appear" items that now have volume and pages
    by_doi = {doi_of(w.get("doi")): w for w in works if w.get("doi")}
    for p in journals:
        if p.get("status") != "To appear":
            continue
        w = by_doi.get(doi_of(p.get("url")))
        ref = ref_of((w or {}).get("biblio") or {})
        if ref and not p.get("ref"):
            p["ref"] = ref
            p["year"] = w.get("publication_year") or p["year"]
            del p["status"]
            changes.append(f"published: {plain(p['title'])} -> {ref}")

    if not changes:
        print("No changes: the page already lists every article found on OpenAlex.")
        return
    now = datetime.date.today()
    data["updated"] = f"{MONTHS[now.month - 1]} {now.year}"
    print("\n".join(changes))
    if dry:
        print("(dry run: data.js not written)")
        return
    DATA_FILE.write_text(src[:i] + json.dumps(data, indent=1, ensure_ascii=False) + src[j:], encoding="utf-8")


if __name__ == "__main__":
    main()
