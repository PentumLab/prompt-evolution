"""Run the independent prompt evaluator and write a generation report."""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.llm import get_response_from_llm
from agent.config import get_agent_max_output_tokens, get_configured_model, load_hyperagent_config
from agent.usage import usage_context
from domains.prompt_design.evolution_state import rebuild_archive, save_metadata
from domains.prompt_design.evaluator.evaluator_schema import validate_evaluation
from domains.prompt_design.run_context import output_root

EVALUATOR_DIR = Path(__file__).resolve().parent


def _json_object(text):
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("Evaluator did not return a JSON object")


def evaluate(original_prompt, candidate_prompt, model=None, max_tokens=None, mode=None, generation=None, target_kind="candidate"):
    config = load_hyperagent_config()
    evaluator_config = config.get("evaluator", {}) or {}
    configured_mode = config.get("prompt_design_evaluator_mode", evaluator_config.get("mode", "simple"))
    mode = mode or configured_mode
    if mode not in {"simple", "comparison"}:
        raise ValueError("prompt_design_evaluator_mode must be 'simple' or 'comparison'")
    prompt_file = EVALUATOR_DIR / ("evaluator_prompt_comparison.md" if mode == "comparison" else "evaluator_prompt.md")
    instructions = prompt_file.read_text(encoding="utf-8")
    message = "CANDIDATE PROMPT:\n" + candidate_prompt
    if mode == "comparison":
        message = "ORIGINAL PROMPT:\n" + original_prompt + "\n\n" + message
        if target_kind == "original":
            message += (
                "\n\nEVALUATION TARGET: BASELINE\n"
                "The candidate is intentionally identical to the original because this is "
                "the baseline measurement. Evaluate the prompt's absolute scientific and "
                "operational quality on all rubric dimensions. Do not assign zero or reduce "
                "the score merely because no change was made; the absence of change is not "
                "a quality judgment."
            )
    configured_model = model or evaluator_config.get("model") or get_configured_model(
        "prompt_design_evaluator", "openai/gpt-4o"
    )
    if max_tokens is not None:
        configured_limit = max_tokens
    elif "max_output_tokens" in evaluator_config:
        configured_limit = evaluator_config["max_output_tokens"]
    else:
        configured_limit = get_agent_max_output_tokens("prompt_design_evaluator")
    with usage_context(
        agent_role="prompt_design_evaluator",
        metadata={
            "domain": "prompt_design",
            "evaluator_mode": mode,
            "target_generation": generation,
            "evaluation_target": target_kind,
        },
    ):
        response, _, _ = get_response_from_llm(
            msg=message,
            model=configured_model,
            max_tokens=configured_limit,
            system_prompt=instructions,
        )
    return response, _json_object(response), mode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--original-prompt", type=Path, required=True)
    parser.add_argument("--candidate-prompt", type=Path, required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--mode", choices=["simple", "comparison"], default=None)
    parser.add_argument("--output-suffix", default=None, help="Write variant files such as report_gemma_simple.json without changing canonical metadata")
    parser.add_argument("--output-directory", type=Path, default=None, help="Optional directory for variant output files")
    parser.add_argument("--target-kind", choices=["candidate", "original"], default="candidate")
    args = parser.parse_args()
    generation_dir = args.output_directory or (output_root() / f"gen_{args.generation:03d}")
    suffix = f"_{args.output_suffix}" if args.output_suffix else ""
    evaluation_path = generation_dir / f"evaluation{suffix}.json"
    report_path = generation_dir / f"report{suffix}.json"
    raw_response = None
    parsed = None
    mode = args.mode
    try:
        raw_response, parsed, mode = evaluate(
            args.original_prompt.read_text(encoding="utf-8"),
            args.candidate_prompt.read_text(encoding="utf-8"),
            model=args.model, max_tokens=args.max_output_tokens, mode=args.mode, generation=args.generation,
            target_kind=args.target_kind,
        )
        try:
            result = validate_evaluation(parsed)
            repair = None
        except ValueError as error:
            components = ("methodology", "consistency", "robustness", "efficiency")
            if "score must equal" not in str(error) or any(key not in parsed for key in components):
                raise
            repaired_score = sum(parsed[key] for key in components)
            result = validate_evaluation({**parsed, "score": repaired_score})
            repair = {"field": "score", "original": parsed.get("score"), "corrected": repaired_score, "reason": str(error)}
        evaluation = {"generation": args.generation, "mode": mode, "target": args.target_kind, "raw_response": raw_response, "parsed": result, "valid": True, "repair": repair}
        if repair:
            evaluation["parsed_raw"] = parsed
    except Exception as exc:
        evaluation = {"generation": args.generation, "mode": mode, "target": args.target_kind, "raw_response": raw_response, "parsed": parsed, "valid": False, "error": str(exc)}
        generation_dir.mkdir(parents=True, exist_ok=True)
        evaluation_path.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        raise
    generation_dir.mkdir(parents=True, exist_ok=True)
    evaluation_path.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = {"overall_score": result["score"] / 100, **result}
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if not args.output_suffix:
        save_metadata(args.generation, {"status": "evaluated", "score": result["score"], "valid_parent": True})
        rebuild_archive()
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
