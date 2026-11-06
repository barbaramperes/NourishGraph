"""
Independent check of factual plausibility (AIH026410167 revision, Reviewer 1, point 3).

The plausibility verdicts in the ablation and baseline runs come from gpt-4o-mini, the same model
that generates the responses. This script asks a model from another family (Anthropic Claude) the
same question, with the same prompt and the same input as the original evaluator, for every stored
science response, and reports both verdicts side by side.

Needs the Anthropic SDK and a key in your local .env (never paste it anywhere else):
    pip install anthropic
    ANTHROPIC_API_KEY=...            # line in .env

Usage:
    python scripts/rescore_plausibility_independent.py \
        evaluation/v5/ablation_v5_raw_20261105_1927.jsonl \
        evaluation/v5/vanilla_v5_raw_20261106_1723.jsonl
    python scripts/rescore_plausibility_independent.py <files> --model claude-opus-5-5

No responses are generated; about 60 evaluator calls are made.
"""
import argparse, json, os, time

DEFAULT_MODEL = "claude-sonnet-5-5"
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
        kwargs = dict(model=model, max_tokens=150,
                      messages=[{"role": "user", "content": prompt_for(query, response)}])
        try:
            msg = client.messages.create(temperature=0, **kwargs)
        except anthropic.BadRequestError:
            msg = client.messages.create(**kwargs)  # models that do not accept a temperature
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return "PASS" in text.split("\n")[0].upper(), text

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

    out = []
    for r in science:
        ok, text = ask(r["query"], r["final_response"])
        out.append({"config": r["config"], "query": r["query"], "original_pass": bool(r.get("judge_pass")),
                    "original_reason": r.get("judge_text"), "independent_pass": ok,
                    "independent_reason": text, "independent_model": args.model})
        print(f"  {r['config']:<20} gpt-4o-mini={'PASS' if r.get('judge_pass') else 'FAIL'}  "
              f"{args.model}={'PASS' if ok else 'FAIL'}  {r['query'][:45]}")

    os.makedirs("evaluation/v5", exist_ok=True)
    path = f"evaluation/v5/plausibility_independent_{time.strftime('%Y%m%d_%H%M')}.jsonl"
    with open(path, "w") as f:
        for row in out:
            f.write(json.dumps(row) + "\n")

    print(f"\n{'config':<20} {'gpt-4o-mini':>12} {args.model:>18} {'agree':>6}")
    for cfg in dict.fromkeys(o["config"] for o in out):
        sub = [o for o in out if o["config"] == cfg]
        print(f"{cfg:<20} {sum(o['original_pass'] for o in sub):>9}/{len(sub):<2} "
              f"{sum(o['independent_pass'] for o in sub):>15}/{len(sub):<2} "
              f"{sum(o['original_pass'] == o['independent_pass'] for o in sub):>4}/{len(sub)}")
    print("\nDisagreements:")
    for o in out:
        if o["original_pass"] != o["independent_pass"]:
            print(f"  {o['config']:<20} {o['query']}\n    {o['independent_reason'][:300]}")
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
