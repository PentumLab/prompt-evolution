"""Evaluate every available generation with configured model/mode variants."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
OUTPUT_DIR = ROOT_DIR / "outputs" / "prompt_design"


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", required=True, metavar="NAME=MODEL", help="Repeat for each model, e.g. gemma=hosted_vllm/gemma-4")
    parser.add_argument("--mode", action="append", choices=["simple", "comparison"], default=None)
    parser.add_argument("--generation", type=int, action="append")
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--no-original", action="store_true", help="Do not evaluate the source prompt as a separate baseline")
    args = parser.parse_args()
    modes = args.mode or ["simple", "comparison"]
    models = []
    for value in args.model:
        if "=" not in value:
            parser.error("--model must have NAME=MODEL format")
        name, model = value.split("=", 1)
        models.append((safe_name(name), model))
    generations = args.generation or sorted(
        int(path.name[4:]) for path in OUTPUT_DIR.glob("gen_[0-9][0-9][0-9]")
        if (path / "candidate_prompt.txt").exists()
    )
    original = ROOT_DIR / "domains" / "prompt_design" / "prompt.md"
    failures = 0
    if not args.no_original:
        baseline_dir = OUTPUT_DIR / "baseline"
        for model_name, model in models:
            for mode in modes:
                suffix = f"{model_name}_{mode}"
                command = [sys.executable, str(ROOT_DIR / "domains/prompt_design/evaluator/evaluator_runner.py"), "--generation", "0", "--original-prompt", str(original), "--candidate-prompt", str(original), "--model", model, "--mode", mode, "--target-kind", "original", "--output-suffix", suffix, "--output-directory", str(baseline_dir)]
                if args.max_output_tokens is not None:
                    command += ["--max-output-tokens", str(args.max_output_tokens)]
                print(f"Evaluating original prompt: {suffix}")
                result = subprocess.run(command, cwd=ROOT_DIR)
                if result.returncode:
                    failures += 1
    for generation in generations:
        candidate = OUTPUT_DIR / f"gen_{generation:03d}" / "candidate_prompt.txt"
        for model_name, model in models:
            for mode in modes:
                suffix = f"{model_name}_{mode}"
                command = [sys.executable, str(ROOT_DIR / "domains/prompt_design/evaluator/evaluator_runner.py"), "--generation", str(generation), "--original-prompt", str(original), "--candidate-prompt", str(candidate), "--model", model, "--mode", mode, "--output-suffix", suffix]
                if args.max_output_tokens is not None:
                    command += ["--max-output-tokens", str(args.max_output_tokens)]
                print(f"Evaluating gen_{generation:03d}: {suffix}")
                result = subprocess.run(command, cwd=ROOT_DIR)
                if result.returncode:
                    failures += 1
    print(f"Completed variants for {len(generations)} generations; failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
