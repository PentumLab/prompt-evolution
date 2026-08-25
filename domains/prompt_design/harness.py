import argparse
from pathlib import Path

from prompt_design_agent import generate_prompt


BASE_DIR = Path(__file__).parent
TASK_FILE = BASE_DIR / "task.md"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, required=True)
    args = parser.parse_args()

    task = TASK_FILE.read_text(encoding="utf-8")

    response = generate_prompt(task)

    output_dir = Path(
        f"outputs/prompt_design/gen_{args.generation:03d}"
    )
    output_file = output_dir / "candidate_prompt.txt"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file.write_text(response, encoding="utf-8")

    print(f"Candidate written to: {output_file}")


if __name__ == "__main__":
    main()
