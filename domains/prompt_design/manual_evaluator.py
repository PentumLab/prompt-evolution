import argparse
import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, required=True)
    args = parser.parse_args()

    generation_dir = (
        ROOT_DIR
        / "outputs"
        / "prompt_design"
        / f"gen_{args.generation:03d}"
    )

    eval_file = generation_dir / "manual_evaluation.json"
    report_file = generation_dir / "report.json"

    data = json.loads(eval_file.read_text(encoding="utf-8"))

    required = [
        "score",
        "methodology",
        "consistency",
        "robustness",
        "efficiency",
        "feedback",
    ]

    for key in required:
        if key not in data:
            raise ValueError(f"Missing field: {key}")

    components = [
        data["methodology"],
        data["consistency"],
        data["robustness"],
        data["efficiency"],
    ]

    if any(not 0 <= value <= 25 for value in components):
        raise ValueError("Each component score must be between 0 and 25")

    total = sum(components)

    if total != data["score"]:
        raise ValueError(
            f"Score mismatch: components sum to {total}, "
            f"but score is {data['score']}"
        )

    report = {
        "overall_score": data["score"] / 100,
        "score": data["score"],
        "methodology": data["methodology"],
        "consistency": data["consistency"],
        "robustness": data["robustness"],
        "efficiency": data["efficiency"],
        "feedback": data["feedback"],
    }

    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Report written to: {report_file}")
    print(f"Overall score: {report['overall_score']}")


if __name__ == "__main__":
    main()
