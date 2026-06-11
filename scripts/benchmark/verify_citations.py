"""
NourishGraph LLM Benchmark — Citation Verification

Extracts citations from science-agent responses (Q11-Q15) and
cross-references them against the 88-paper Pinecone corpus to
compute Citation Validity Rate per model.

Detects hallucinated citations (fabricated authors/years not in corpus).

Usage:
    python scripts/benchmark/verify_citations.py results/benchmark_raw_XXXX.json
    python scripts/benchmark/verify_citations.py --latest
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# CORPUS: Known papers in the Pinecone index
# ============================================================

def load_corpus_from_papers() -> Set[str]:
    """
    Build a set of known citation keys from the papers/ directory.
    
    Format:  "Author(s) (Year)" → normalised to lowercase
    We parse filenames and the first few lines of each .txt for author/year.
    """
    papers_dir = PROJECT_ROOT / "papers" / "txt"
    corpus_keys = set()
    
    if not papers_dir.exists():
        print(f"  ⚠️  papers/txt/ directory not found — using fallback corpus")
        return _fallback_corpus()
    
    for txt_file in papers_dir.glob("*.txt"):
        filename = txt_file.stem.lower()
        
        # Try to extract author_year from filename patterns like:
        # "smith_2023.txt", "smith_et_al_2024.txt", etc.
        parts = filename.replace("-", "_").split("_")
        
        # Read first 10 lines for title/author info
        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                header = " ".join(f.readline() for _ in range(10)).lower()
        except Exception:
            header = ""
        
        # Extract any years (2019-2026)
        years = re.findall(r'(20[12]\d)', filename + " " + header)
        
        # Extract author-like words from filename
        author_parts = [p for p in parts if p.isalpha() and len(p) > 2 and p not in ("the", "and", "for", "with", "from")]
        
        for year in years:
            for author in author_parts[:3]:
                corpus_keys.add(f"{author} {year}")
                corpus_keys.add(f"{author} et al {year}")
                corpus_keys.add(f"{author} et al. {year}")
        
        # Also add the full filename as a key
        corpus_keys.add(filename)
    
    return corpus_keys


def _fallback_corpus() -> Set[str]:
    """Hardcoded known citations from the 88-paper corpus (sample)."""
    return {
        # Sample of known papers — extend as needed
        "campbell 2017", "jager 2017", "morton 2018",
        "schoenfeld 2018", "stokes 2018", "kreider 2017",
        "antonio 2014", "phillips 2016", "tipton 2018",
        "helms 2014", "maughan 2018", "thomas 2016",
        "kerksick 2018", "trexler 2014", "henselmans 2014",
        "areta 2013", "churchward-venne 2012", "moore 2015",
        "murphy 2015", "witard 2014",
    }


def extract_citations(text: str) -> List[Dict[str, str]]:
    """
    Extract citation references from response text.
    
    Detects patterns like:
    - (Smith et al., 2023)
    - (Smith & Jones, 2024)
    - (Smith, 2023)
    - Smith et al. (2023)
    - (WHO, 2021)
    """
    citations = []
    
    # Pattern 1: (Author et al., Year) or (Author, Year) — parenthetical
    pattern1 = r'\(([A-Z][a-zA-Z\-]+(?:\s+(?:et\s+al\.?|&\s+[A-Z][a-zA-Z\-]+))?),?\s*(\d{4})\)'
    for match in re.finditer(pattern1, text):
        citations.append({
            "raw": match.group(0),
            "author": match.group(1).strip(),
            "year": match.group(2),
            "key": f"{match.group(1).strip().lower()} {match.group(2)}",
        })
    
    # Pattern 2: Author et al. (Year) — narrative
    pattern2 = r'([A-Z][a-zA-Z\-]+\s+et\s+al\.?)\s+\((\d{4})\)'
    for match in re.finditer(pattern2, text):
        citations.append({
            "raw": match.group(0),
            "author": match.group(1).strip(),
            "year": match.group(2),
            "key": f"{match.group(1).strip().lower()} {match.group(2)}",
        })
    
    # Pattern 3: Author & Author (Year) — narrative
    pattern3 = r'([A-Z][a-zA-Z\-]+\s+&\s+[A-Z][a-zA-Z\-]+)\s+\((\d{4})\)'
    for match in re.finditer(pattern3, text):
        citations.append({
            "raw": match.group(0),
            "author": match.group(1).strip(),
            "year": match.group(2),
            "key": f"{match.group(1).strip().lower()} {match.group(2)}",
        })
    
    # Deduplicate by raw text
    seen = set()
    unique = []
    for c in citations:
        if c["raw"] not in seen:
            seen.add(c["raw"])
            unique.append(c)
    
    return unique


def verify_citation(citation: Dict[str, str], corpus: Set[str]) -> bool:
    """Check if a citation exists in the corpus."""
    key = citation["key"]
    
    # Direct match
    if key in corpus:
        return True
    
    # Try without "et al."
    simple_key = key.replace(" et al.", "").replace(" et al", "")
    if simple_key in corpus:
        return True
    
    # Try first author's surname only
    author = citation["author"].split()[0].lower()
    year = citation["year"]
    if f"{author} {year}" in corpus:
        return True
    if f"{author} et al {year}" in corpus:
        return True
    if f"{author} et al. {year}" in corpus:
        return True
    
    # Fuzzy: check if author surname appears in any corpus key with same year
    for ck in corpus:
        if author in ck and year in ck:
            return True
    
    return False


def analyse_citations(raw_json_path: str) -> Dict:
    """
    Main analysis: extract and verify citations from Q11-Q15 responses.
    
    Returns:
        Dict with per-model citation stats
    """
    with open(raw_json_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    corpus = load_corpus_from_papers()
    print(f"  📚 Corpus: {len(corpus)} citation keys loaded")
    
    citation_queries = [r for r in results if r["category"] == "citation"]
    
    models_data: Dict[str, List] = {}
    for row in citation_queries:
        mid = row["model"]
        models_data.setdefault(mid, []).append(row)
    
    analysis = {}
    
    for model_id, rows in models_data.items():
        model_name = rows[0]["model_name"]
        total_citations = 0
        valid_citations = 0
        hallucinated = []
        all_citations = []
        
        for row in rows:
            response = row.get("response_text", "")
            citations = extract_citations(response)
            
            for c in citations:
                total_citations += 1
                is_valid = verify_citation(c, corpus)
                c["valid"] = is_valid
                c["query_id"] = row["query_id"]
                all_citations.append(c)
                
                if is_valid:
                    valid_citations += 1
                else:
                    hallucinated.append(c)
        
        validity_rate = (valid_citations / total_citations * 100) if total_citations > 0 else 0
        
        analysis[model_id] = {
            "model_name": model_name,
            "total_citations": total_citations,
            "valid_citations": valid_citations,
            "hallucinated_citations": len(hallucinated),
            "validity_rate": round(validity_rate, 1),
            "hallucinated_list": hallucinated,
            "all_citations": all_citations,
        }
    
    return analysis


def print_report(analysis: Dict) -> str:
    """Print and return a formatted citation verification report."""
    lines = [
        "\n" + "=" * 60,
        "  CITATION VERIFICATION REPORT",
        "=" * 60,
    ]
    
    for model_id, data in analysis.items():
        lines.extend([
            f"\n  {data['model_name']}",
            f"    Total citations extracted:    {data['total_citations']}",
            f"    Valid (in corpus):             {data['valid_citations']}",
            f"    Hallucinated (not in corpus):  {data['hallucinated_citations']}",
            f"    Validity Rate:                 {data['validity_rate']:.1f}%",
        ])
        
        if data["hallucinated_list"]:
            lines.append(f"    Hallucinated citations:")
            for h in data["hallucinated_list"]:
                lines.append(f"      ⚠️  {h['raw']} (from {h['query_id']})")
    
    lines.extend(["", "=" * 60, ""])
    
    report = "\n".join(lines)
    print(report)
    return report


def find_latest_json() -> Optional[str]:
    """Find the most recent raw JSON file in results/."""
    results_dir = PROJECT_ROOT / "scripts" / "benchmark" / "results"
    if not results_dir.exists():
        return None
    jsons = sorted(results_dir.glob("benchmark_raw_*.json"))
    return str(jsons[-1]) if jsons else None


def main():
    parser = argparse.ArgumentParser(description="Verify citations from NourishGraph benchmark")
    parser.add_argument("json_path", nargs="?", help="Path to benchmark raw JSON")
    parser.add_argument("--latest", action="store_true", help="Use latest raw JSON")
    args = parser.parse_args()
    
    json_path = args.json_path
    if not json_path and args.latest:
        json_path = find_latest_json()
    if not json_path:
        json_path = find_latest_json()
    if not json_path:
        print("❌ No raw JSON found. Run run_benchmark.py first.")
        sys.exit(1)
    
    print(f"\n📂 Loading: {json_path}")
    analysis = analyse_citations(json_path)
    report = print_report(analysis)
    
    # Save report
    output_dir = Path(json_path).parent
    report_path = output_dir / "citation_verification.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ Report saved: {report_path}")
    
    # Save JSON
    json_out_path = output_dir / "citation_verification.json"
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
    print(f"✅ JSON saved: {json_out_path}\n")


if __name__ == "__main__":
    main()
