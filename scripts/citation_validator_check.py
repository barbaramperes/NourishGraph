"""
Check citation post-validation, before and after the November 2026 correction (AIH026410167).

The validator as run in the ablation studies (v4, v5) compared only the first author's
surname, read the last word of each name (so "Abdelhamid AS" became "as"), ignored the
year and missed hyphenated names, "A and B" citations and numeric citations. This script
runs that version (copied below, unchanged) and the corrected one in
app/agents/citation_validator.py on:

1. a probe of genuine and fabricated citations built from the papers actually retrieved
   in the stored full-system run (plus one corpus paper that was not retrieved);
2. every science response stored in an ablation v5 raw file.

No API calls. Usage:
    python scripts/citation_validator_check.py evaluation/v5/ablation_v5_raw_20261105_1927.jsonl
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.citation_validator import validate_inline_citations as current_validate

CORPUS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "app", "data", "paper_metadata.json")


# ------------------------------------------------------------
# The validator as run in v4 and v5 (unchanged copy)
# ------------------------------------------------------------

def legacy_extract(response_text):
    patterns = [
        r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s*(\d{4})\)',
        r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)',
        r'\[([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s*(\d{4})\]',
    ]
    citations = []
    for pattern in patterns:
        for match in re.findall(pattern, response_text):
            citations.append({'authors': match[0], 'year': int(match[1]) if match[1].isdigit() else None})
    return citations


def legacy_validate(response_text, search_results):
    extracted = legacy_extract(response_text)
    valid_authors = set()
    for paper in search_results:
        metadata = paper.get('metadata', {})
        authors = metadata.get('authors', '') or paper.get('authors', '')
        year = metadata.get('year') or paper.get('year')
        if authors:
            if isinstance(authors, list):
                authors = ', '.join(str(a) for a in authors)
            first_author = authors.split(',')[0].split()[-1] if authors else ''
            if first_author:
                valid_authors.add((first_author.lower(), year))
    validated = [c for c in extracted
                 if any(c['authors'].replace(' et al.', '').lower() in va[0].lower() for va in valid_authors)]
    return {'total_citations': len(extracted), 'validated': len(validated),
            'unvalidated': len(extracted) - len(validated)}


# ------------------------------------------------------------
# Probe
# ------------------------------------------------------------

def surname(author: str) -> str:
    """'Abdelhamid AS' -> 'Abdelhamid'; 'Javier Delgado-Lista' -> 'Delgado-Lista'."""
    parts = author.split()
    if len(parts) > 1 and re.fullmatch(r"[A-Z]{1,3}", parts[-1]):
        return parts[0]
    return parts[-1]


def build_probe(papers: list, corpus: list) -> list:
    """(case, text, number of fabricated citations, number of genuine citations)."""
    with_year = [p for p in papers if p.get("authors") and p.get("year")]
    given = next((p for p in with_year if "-" in surname(p["authors"][0])
                  and not re.fullmatch(r"[A-Z]{1,3}", p["authors"][0].split()[-1])), with_year[0])
    initials = next((p for p in with_year if re.fullmatch(r"[A-Z]{1,3}", p["authors"][0].split()[-1])), None)
    multi = next((p for p in with_year if len(p["authors"]) >= 2), given)
    s1, y1 = surname(given["authors"][0]), given["year"]
    s2a, s2b, y2 = surname(multi["authors"][0]), surname(multi["authors"][1]), multi["year"]
    retrieved = {surname(a).lower() for p in papers for a in p.get("authors", [])}
    other = next(p for p in corpus if p.get("authors") and p.get("year")
                 and surname(p["authors"][0]).lower() not in retrieved)
    so, yo = surname(other["authors"][0]), other["year"]

    cases = [
        ("genuine: first author", f"Omega-3 lowers triglycerides ({s1} et al., {y1}).", 0, 1),
        ("genuine: narrative form", f"{s1} et al. ({y1}) reported lower triglycerides.", 0, 1),
        ("genuine: co-author cited", f"A second finding ({s2b} et al., {y2}).", 0, 1),
        ("genuine: two authors", f"Both agree ({s2a} and {s2b}, {y2}).", 0, 1),
    ]
    if initials:
        si, yi = surname(initials["authors"][0]), initials["year"]
        cases += [
            ("genuine: name stored 'Surname Initials'", f"A meta-analysis found no effect ({si} et al., {yi}).", 0, 1),
            ("genuine: two in one parenthesis", f"Evidence is mixed ({s1} et al., {y1}; {si} et al., {yi}).", 0, 2),
        ]
    for fake in ["Hargreaves", "Okonkwo", "Vandersloot", "Pemberton", "Quintanilla"]:
        cases.append((f"fabricated: author {fake}", f"Fiber improves satiety ({fake} et al., 2021).", 1, 0))
    cases += [
        ("fabricated: real author, wrong year", f"A related finding ({s1} et al., 1987).", 1, 0),
        ("fabricated: numeric [1]", "Probiotics reduce bloating [1].", 1, 0),
        ("fabricated: 'A and B'", "Vitamin D supports immunity (Hargreaves and Pemberton, 2019).", 1, 0),
        ("not retrieved: corpus paper", f"As shown before ({so} et al., {yo}).", 1, 0),
    ]
    return cases


def run_probe(papers, corpus):
    cases = build_probe(papers, corpus)
    print(f"Probe ({len(cases)} cases, papers retrieved in the stored full-system run)")
    print(f"  {'case':<42} {'legacy':>7} {'current':>8}   flagged / citations")
    tally = {"legacy": [0, 0, 0, 0], "current": [0, 0, 0, 0]}  # fake flagged, fake total, genuine flagged, genuine total
    for name, text, n_fake, n_real in cases:
        out = {}
        for label, fn in (("legacy", legacy_validate), ("current", current_validate)):
            r = fn(text, papers)
            out[label] = f"{r['unvalidated']}/{r['total_citations']}"
            t = tally[label]
            if n_fake:
                t[0] += min(r["unvalidated"], n_fake); t[1] += n_fake
            else:
                t[2] += min(r["unvalidated"], n_real); t[3] += n_real
        print(f"  {name:<42} {out['legacy']:>7} {out['current']:>8}")
    for label, t in tally.items():
        print(f"  {label:<8} fabricated or untraceable flagged {t[0]}/{t[1]}; genuine flagged {t[2]}/{t[3]}")
    print()
    return tally


def run_audit(rows):
    print("Stored science responses")
    print(f"  {'config':<20} {'legacy: extracted / flagged':>28} {'current: extracted / flagged':>30}")
    for cfg in dict.fromkeys(r["config"] for r in rows):
        sci = [r for r in rows if r["config"] == cfg and r["category"] == "science" and r.get("papers")]
        if not sci:
            continue
        le = lf = ce = cf = 0
        reasons = {}
        for r in sci:
            a, b = legacy_validate(r["final_response"], r["papers"]), current_validate(r["final_response"], r["papers"])
            le += a["total_citations"]; lf += a["unvalidated"]
            ce += b["total_citations"]; cf += b["unvalidated"]
            for u in b["unvalidated_list"]:
                reasons[u["reason"]] = reasons.get(u["reason"], 0) + 1
        print(f"  {cfg:<20} {le:>14} / {lf:<11} {ce:>16} / {cf:<11} {reasons or ''}")
    print()


def main(path):
    rows = [json.loads(l) for l in open(path)]
    corpus = json.load(open(CORPUS_PATH))
    papers, seen = [], set()
    for r in rows:
        if r["config"] == "full_system" and r["category"] == "science":
            for p in r.get("papers") or []:
                key = (p.get("title"), p.get("year"))
                if key not in seen:
                    seen.add(key); papers.append(p)
    run_probe(papers, corpus)
    run_audit(rows)


if __name__ == "__main__":
    main(sys.argv[1])
