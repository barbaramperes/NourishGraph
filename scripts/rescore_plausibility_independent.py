"""
Independent check of factual plausibility (AIH026410167 revision, Reviewer 1, point 3).

The plausibility verdicts in the ablation and baseline runs come from gpt-4o-mini, the same model
that generates the responses. This script asks a model from another family (Anthropic Claude) the
same question, with the same prompt and the same input as the original evaluator, for every stored
science response, and reports both verdicts side by side.

Needs the Anthropic SDK and a key in your local .env (never paste it anywhere else):
    pip install anthropic
    ANTHROPIC_API_KEY=...            # line in .env

Current Claude models accept no sampling settings (temperature etc.), so the verdicts are not
fixed by a temperature of 0 as gpt-4o-mini's were; every verdict and its reason is saved instead.
Server-side refusal fallback is on: if the evaluator declines an item, another Claude model answers
it, and the model that answered is recorded for that item ("served_by").

Usage:
    python scripts/rescore_plausibility_independent.py \
        evaluation/v5/ablation_v5_raw_20261105_1927.jsonl \
        evaluation/v5/vanilla_v5_raw_20261106_1723.jsonl
    python scripts/rescore_plausibility_independent.py <files> --model claude-sonnet-5-5

No responses are generated; about 60 evaluator calls are made (roughly US$1 to 3 with the default model).
"""
import argparse, json, os, time

DEFAULT_MODEL = "claude-opus-5-5"
CRITERIA = "Is the information factually accurate and evidence-based?"


def prompt_for(query: str, response: str) -> str:
    """Identical to the evaluator prompt of run_ablation_study_v5.judge (response cut at 1,500 characters)."""
    return f"""You are a strict evaluator. Answer ONLY 'PASS' or 'FAIL' on the first line, then a brief reason.

Query: {query}
Response: {response[:1500]}

Criteria: {CRITERIA}"""


def make_judge(model: str):
    from dotenv import load_dotenv
    load_dotenv()
    import anthropic
    client = anthropic.Anthropic()

    def ask(query: str, response: str):
        msg = client.beta.messages.create(
            model=model,
            max_tokens=16000,                       # thinking counts toward this limit
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": prompt_for(query, response)}],
        )
        if msg.stop_reason == "refusal":
            return None, "REFUSED", msg.model
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        return "PASS" in text.split("\n")[0].upper(), text, msg.model

    return ask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    rows = []
    for path in args.files:
        rows += [{"config": "unconstrained", **json.loads(l)} for l in open(path)]
    science = [r for r in rows if r["category"] == "science"]
    ask = make_judge(args.model)

    os.makedirs("evaluation/v5", exist_ok=True)
    path = f"evaluation/v5/plausibility_independent_{time.strftime('%Y%m%d_%H%M')}.jsonl"
    out = []
    with open(path, "w") as f:  # written item by item, so an interruption keeps what was done
        for r in science:
            ok, text, served_by = ask(r["query"], r["final_response"])
            row = {"config": r["config"], "query": r["query"], "original_pass": bool(r.get("judge_pass")),
                   "original_reason": r.get("judge_text"), "independent_pass": ok,
                   "independent_reason": text, "independent_model": args.model, "served_by": served_by}
            out.append(row)
            f.write(json.dumps(row) + "\n"); f.flush()
            verdict = "REFUSED" if ok is None else ("PASS" if ok else "FAIL")
            note = "" if served_by == args.model else f" (answered by {served_by})"
            print(f"  {r['config']:<20} gpt-4o-mini={'PASS' if r.get('judge_pass') else 'FAIL'}  "
                  f"{args.model}={verdict}{note}  {r['query'][:45]}")

    print(f"\n{'config':<20} {'gpt-4o-mini':>12} {args.model:>18} {'agree':>6}")
    for cfg in dict.fromkeys(o["config"] for o in out):
        sub = [o for o in out if o["config"] == cfg]
        print(f"{cfg:<20} {sum(o['original_pass'] for o in sub):>9}/{len(sub):<2} "
              f"{sum(bool(o['independent_pass']) for o in sub):>15}/{len(sub):<2} "
              f"{sum(o['original_pass'] == o['independent_pass'] for o in sub):>4}/{len(sub)}")
    print("\nDisagreements:")
    for o in out:
        if o["original_pass"] != o["independent_pass"]:
            print(f"  {o['config']:<20} {o['query']}\n    {o['independent_reason'][:300]}")
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
