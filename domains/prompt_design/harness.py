import argparse
import importlib.util
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.usage import usage_context
from domains.prompt_design.evolution_state import (
    save_metadata,
    snapshot_agent,
    snapshot_path,
)


BASE_DIR = Path(__file__).parent
SOURCE_PROMPT_FILE = BASE_DIR / "prompt.md"
GUIDANCE_FILE = BASE_DIR / "guidance.md"


def build_improvement_task(source_prompt, guidance):
    return f"""Improve the existing prompt below.

The goal is not to replace it with an unrelated prompt. First infer what the
prompt is meant to do, then improve clarity, robustness, structure,
operational rules, and efficiency while preserving its core purpose,
audience, constraints, and output contract.

Return only the improved prompt.

SOURCE PROMPT TO IMPROVE:
{source_prompt}

IMPROVEMENT GUIDANCE:
{guidance}
"""


def load_generate_prompt(generation):
    agent_snapshot = snapshot_path(generation)
    if not agent_snapshot.exists():
        agent_snapshot = snapshot_agent(generation)

    module_name = f"prompt_design_agent_gen_{generation:03d}"
    spec = importlib.util.spec_from_file_location(module_name, agent_snapshot)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load prompt design agent: {agent_snapshot}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generate_prompt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument(
        "--source-prompt",
        default=str(SOURCE_PROMPT_FILE),
        help="Path to the existing prompt that should be improved.",
    )
    parser.add_argument(
        "--guidance",
        default=str(GUIDANCE_FILE),
        help="Path to optional improvement and evaluation guidance.",
    )
    args = parser.parse_args()

    source_prompt_path = Path(args.source_prompt).expanduser()
    guidance_path = Path(args.guidance).expanduser()
    source_prompt = source_prompt_path.read_text(encoding="utf-8")
    guidance = guidance_path.read_text(encoding="utf-8")
    task = build_improvement_task(source_prompt, guidance)
    generate_prompt = load_generate_prompt(args.generation)

    with usage_context(
        metadata={
            "domain": "prompt_design",
            "generation": args.generation,
        }
    ):
        response = generate_prompt(task)

    output_dir = (
        ROOT_DIR
        / "outputs"
        / "prompt_design"
        / f"gen_{args.generation:03d}"
    )
    output_file = output_dir / "candidate_prompt.txt"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file.write_text(response, encoding="utf-8")
    save_metadata(
        args.generation,
        {
            "candidate_prompt": str(output_file),
            "agent_snapshot": str(snapshot_path(args.generation)),
            "source_prompt": str(source_prompt_path),
            "guidance": str(guidance_path),
        },
    )

    print(f"Candidate written to: {output_file}")


if __name__ == "__main__":
    main()
