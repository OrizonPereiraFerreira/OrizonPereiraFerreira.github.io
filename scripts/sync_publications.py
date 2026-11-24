#!/usr/bin/env python3
"""Update js/data.js from OpenAlex (https://openalex.org) and arXiv.

OpenAlex indexes the same literature as Google Scholar but has an open API, so the
page can be refreshed automatically (Google Scholar blocks automated access).
The author is identified by ORCID on OpenAlex and by name on arXiv.

What it does:
  * Preprints: adds recent arXiv preprints that are not on the page yet;
  * when an item in "Preprints" comes out in a journal, moves it to
    "Articles in journals" (keeping its code/PDF links). The published version is
    recognised by its arXiv link on OpenAlex, so a changed title does not matter;
  * adds journal articles that are not on the page yet (matched by DOI and by title);
  * fills volume/pages of items marked "To appear" once they are published.

It never removes or rewrites anything else. Nothing listed in scripts/sync-ignore.txt
(one DOI or arXiv id per line) is proposed, and neither is anything that was in a
sync pull request you closed without merging.

Usage:  python3 scripts/sync_publications.py [--dry-run]
"""
import datetime
import difflib
import html
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ORCID = "0000-0002-5758-0320"
ME = "O. P. Ferreira"
ARXIV_AUTHOR = 'au:"O. P. Ferreira"'
PREPRINT_YEARS = 3          # arXiv preprints older than this are not proposed
REPO = os.environ.get("GITHUB_REPOSITORY", "OrizonPereiraFerreira/OrizonPereiraFerreira.github.io")
SYNC_BRANCH = "sync-publications"
ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "js" / "data.js"
IGNORE_FILE = ROOT / "scripts" / "sync-ignore.txt"
JOURNALS = "Articles in journals"
PREPRINTS = "Preprints"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
ATOM = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}


def fetch(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": "academic-page-sync/1.0", "Accept": accept})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def openalex_works():
    works, cursor = [], "*"
    while cursor:
        q = urllib.parse.urlencode({"filter": "author.orcid:" + ORCID, "per-page": 200, "cursor": cursor})
        page = json.loads(fetch("https://api.openalex.org/works?" + q))
        works += page["results"]
        cursor = page["meta"].get("next_cursor") if page["results"] else None
    return works


def arxiv_entries():
    q = urllib.parse.urlencode({"search_query": ARXIV_AUTHOR, "max_results": 200,
                                "sortBy": "submittedDate", "sortOrder": "descending"})
    root = ET.fromstring(fetch("https://export.arxiv.org/api/query?" + q, "application/atom+xml"))
    out = []
    for e in root.findall("a:entry", ATOM):
        out.append({
            "id": arxiv_of(e.find("a:id", ATOM).text),
            "title": plain(e.find("a:title", ATOM).text),
            "authors": [plain(a.find("a:name", ATOM).text) for a in e.findall("a:author", ATOM)],
            "date": e.find("a:published", ATOM).text[:10],
        })
    return out


def closed_sync_ids():
    """Ids listed in sync pull requests that were closed without merging."""
    ids = set()
    try:
        url = f"https://api.github.com/repos/{REPO}/pulls?state=closed&per_page=100"
        for pr in json.loads(fetch(url, "application/vnd.github+json")):
            if pr["head"]["ref"] == SYNC_BRANCH and not pr.get("merged_at"):
                ids |= ids_in(pr.get("body") or "")
    except Exception as err:  # the sync still works, it just may propose a refused item again
        print(f"(could not read closed pull requests: {err})", file=sys.stderr)
    return ids


def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def norm(s):
    s = unicodedata.normalize("NFKD", plain(html.unescape(s or ""))).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def similar(a, b):
    a, b = norm(a), norm(b)
    return a == b or (min(len(a), len(b)) > 20 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.9)


def doi_of(s):
    m = re.search(r"10\.\d{4,9}/[^\s\"'<>\]\)]+", s or "")
    d = m.group(0).lower().rstrip(".,") if m else ""
    return "" if d.startswith("10.48550/arxiv") else d


def arxiv_of(s):
    m = re.search(r"arxiv[^0-9]{0,12}(\d{4}\.\d{4,5})", s or "", re.I)
    return "arxiv:" + m.group(1) if m else ""


def ids_in(text):
    ids = set()
    for line in (text or "").splitlines():
        for f in (doi_of, arxiv_of):
            if f(line):
                ids.add(f(line))
    return ids


def item_ids(p):
    ids = set()
    for f in ("url", "pdf", "venueUrl", "venue"):
        ids |= {x for x in (doi_of(p.get(f)), arxiv_of(p.get(f))) if x}
    return ids


def initials(full_name):
    """'Jen-Chih Yao' -> 'J.-C. Yao'; 'Orizon Pereira Ferreira' -> 'O. P. Ferreira'."""
    parts = plain(full_name).replace(".", ". ").split()
    if len(parts) < 2:
        return full_name
    given = ["-".join(x[0].upper() + "." for x in p.split("-") if x) for p in parts[:-1]]
    return " ".join(given + [parts[-1]])


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


def work_arxiv_ids(w):
    return {arxiv_of(l.get("landing_page_url")) for l in w.get("locations", [])} - {""}


def main():
    dry = "--dry-run" in sys.argv
    src = DATA_FILE.read_text(encoding="utf-8")
    i, j = src.index("{"), src.rindex("}") + 1
    data = json.loads(src[i:j])
    groups = {g["name"]: g for g in data["publications"]}
    journals = groups[JOURNALS]["items"]
    preprints = groups[PREPRINTS]["items"]

    ignore = closed_sync_ids()
    if IGNORE_FILE.exists():
        lines = [l for l in IGNORE_FILE.read_text().splitlines() if not l.lstrip().startswith("#")]
        ignore |= ids_in("\n".join(lines))

    def page_ids():
        return set().union(*(item_ids(p) for g in data["publications"] for p in g["items"]))

    # Spellings already used on the page, so new entries look like the old ones
    author_forms, venue_forms = {}, {}
    for g in data["publications"]:
        for p in g["items"]:
            for a in p["authors"]:
                author_forms.setdefault((norm(a.split()[-1]), a[0].upper()), a)
            if p.get("venue"):
                venue_forms.setdefault(norm(p["venue"]), (p["venue"], p.get("venueUrl", "")))

    def short_name(name):
        s = initials(name)
        if s == ME or norm(name) in ("orizonpferreira", "orizonpereiraferreira", "opferreira"):
            return ME
        return author_forms.get((norm(s.split()[-1]), s[0].upper()), s)

    def journal_item(w):
        src_ = (w.get("primary_location") or {}).get("source") or {}
        venue, venue_url = venue_forms.get(norm(src_.get("display_name")), (src_.get("display_name", ""), ""))
        ref = ref_of(w.get("biblio") or {})
        names = []
        for a in w.get("authorships", []):
            if ((a.get("author") or {}).get("orcid") or "").endswith(ORCID):
                names.append(ME)
            else:
                names.append(short_name((a.get("author") or {}).get("display_name") or a.get("raw_author_name") or ""))
        item = {"n": 0, "authors": names, "title": html.escape(plain(w["title"]), quote=False),
                "venue": venue, "ref": ref, "year": w.get("publication_year"),
                "url": "https://doi.org/" + doi_of(w["doi"]), "pdf": "", "code": ""}
        if not ref:
            item["status"] = "To appear"
        if venue_url:
            item["venueUrl"] = venue_url
        return item

    works = openalex_works()
    articles = [w for w in works
                if w.get("type") == "article" and doi_of(w.get("doi")) and plain(w.get("title"))
                and ((w.get("primary_location") or {}).get("source") or {}).get("type") == "journal"]
    by_arxiv = {ax: w for w in articles for ax in work_arxiv_ids(w)}

    changes, added = [], []

    # 1. preprints on the page that are now published
    for pre in list(preprints):
        ax = arxiv_of(pre.get("url")) or arxiv_of(pre.get("venue"))
        w = by_arxiv.get(ax) or next((w for w in articles if similar(w["title"], pre["title"])), None)
        if not w or doi_of(w["doi"]) in ignore:
            continue
        doi = doi_of(w["doi"])
        existing = next((p for p in journals if doi in item_ids(p)), None)
        target = existing or journal_item(w)
        target["code"] = target.get("code") or pre.get("code", "")
        target["pdf"] = target.get("pdf") or pre.get("pdf", "")
        preprints.remove(pre)
        if not existing:
            added.append(target)
        changes.append(f"published: {plain(pre['title'])} -> {target['venue']}, {target['year']} "
                       f"[{ax or 'preprint'} -> {doi}]")

    # 2. journal articles not on the page
    known = page_ids() | {doi_of(p["url"]) for p in added}
    titles = [p["title"] for g in data["publications"] if g["name"] != PREPRINTS for p in g["items"]] + \
             [p["title"] for p in added]
    for w in sorted(articles, key=lambda w: w.get("publication_date") or ""):
        doi = doi_of(w["doi"])
        if doi in known or doi in ignore or any(similar(w["title"], t) for t in titles):
            continue
        item = journal_item(w)
        added.append(item)
        titles.append(item["title"])
        known.add(doi)
        changes.append(f"added article: {plain(w['title'])} ({item['venue']}, {item['year']}) [{doi}]")

    # 3. recent arXiv preprints not on the page and not published yet
    try:
        entries = arxiv_entries()
    except Exception as err:
        entries = []
        print(f"(could not read arXiv: {err})", file=sys.stderr)
    cutoff = str(datetime.date.today().year - PREPRINT_YEARS)
    known = page_ids()
    all_titles = [p["title"] for g in data["publications"] for p in g["items"]] + \
                 [p["title"] for p in added] + [w["title"] for w in articles]
    new_pre = []
    for e in entries:
        if (e["date"] < cutoff or e["id"] in known or e["id"] in ignore or e["id"] in by_arxiv
                or any(similar(e["title"], t) for t in all_titles)):
            continue
        num = e["id"].split(":")[1]
        new_pre.append({"authors": [short_name(a) for a in e["authors"]],
                        "title": html.escape(e["title"], quote=False), "venue": "arXiv:" + num,
                        "ref": "", "year": int(e["date"][:4]), "url": "https://arxiv.org/abs/" + num,
                        "pdf": "", "code": "", "venueUrl": "https://arxiv.org/abs/" + num})
        all_titles.append(e["title"])
        changes.append(f"added preprint: {e['title']} ({e['date'][:4]}) [{e['id']}]")
    preprints[0:0] = sorted(new_pre, key=lambda p: -p["year"])

    # Place each article in its year. If the numbering of that year has a free number,
    # use it; otherwise put it at the top of the year and shift up the numbers above it.
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

    # 4. "To appear" items that now have volume and pages
    by_doi = {doi_of(w.get("doi")): w for w in articles}
    for p in journals:
        if p.get("status") != "To appear" or p in added:
            continue
        w = by_doi.get(doi_of(p.get("url")))
        ref = ref_of((w or {}).get("biblio") or {})
        if ref and not p.get("ref"):
            p["ref"] = ref
            p["year"] = w.get("publication_year") or p["year"]
            del p["status"]
            changes.append(f"volume and pages: {plain(p['title'])} -> {ref} [{doi_of(p['url'])}]")

    if not changes:
        print("No changes: the page is up to date with OpenAlex and arXiv.")
        return
    now = datetime.date.today()
    data["updated"] = f"{MONTHS[now.month - 1]} {now.year}"
    print("\n".join(changes))
    print("If you close this pull request without merging, none of the items above will be proposed again.")
    if dry:
        print("(dry run: data.js not written)")
        return
    DATA_FILE.write_text(src[:i] + json.dumps(data, indent=1, ensure_ascii=False) + src[j:], encoding="utf-8")


if __name__ == "__main__":
    main()
