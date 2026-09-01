import argparse
from pathlib import Path

from agent.usage import usage_context
from prompt_design_agent import generate_prompt


BASE_DIR = Path(__file__).parent
ROOT_DIR = Path(__file__).resolve().parents[2]
TASK_FILE = BASE_DIR / "task.md"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, required=True)
    args = parser.parse_args()

    task = TASK_FILE.read_text(encoding="utf-8")

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

    print(f"Candidate written to: {output_file}")


if __name__ == "__main__":
    main()
