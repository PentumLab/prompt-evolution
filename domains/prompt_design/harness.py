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
TASK_FILE = BASE_DIR / "task.md"


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
    args = parser.parse_args()

    task = TASK_FILE.read_text(encoding="utf-8")
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
        },
    )

    print(f"Candidate written to: {output_file}")


if __name__ == "__main__":
    main()
