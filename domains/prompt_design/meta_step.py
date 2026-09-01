import argparse
import json
from pathlib import Path

from agent.config import get_configured_model
from agent.llm import CLAUDE_HAIKU_45_MODEL
from agent.llm_withtools import chat_with_agent
from agent.usage import usage_context


ROOT_DIR = Path(__file__).resolve().parents[2]


def build_instruction(report, generation, scope):
    target_file = ROOT_DIR / "prompt_design_agent.py"
    task_file = ROOT_DIR / "domains" / "prompt_design" / "task.md"

    common = f"""
You are the Meta-Agent in a prompt-evolution experiment.

Repository:
{ROOT_DIR}

Current generation:
{generation}

Task definition:
{task_file}

Latest evaluation:

Overall score: {report["score"]}/100
Methodology: {report["methodology"]}/25
Consistency: {report["consistency"]}/25
Robustness: {report["robustness"]}/25
Efficiency: {report["efficiency"]}/25

Human feedback:
{report["feedback"]}

Analyze the existing implementation and improve the system based on the
evaluation.

Do not modify evaluation results or the task definition.
Do not merely describe changes. Use the available tools and make actual
changes.

After editing:
1. Inspect the changed files.
2. Run appropriate validation such as py_compile.
3. Fix errors before finishing.
"""

    if scope == "prompt":
        return common + f"""

For this run the evolution scope is PROMPT ONLY.

Target file:
{target_file}

STRICT CONSTRAINTS:
- Preserve generate_prompt(task: str) -> str.
- It must continue to return a Python string.
- Keep the existing single Task-Agent LLM call.
- Do not add runtime evaluator logic or extra model calls.
- Improve the prompt-generation strategy inside generate_prompt().
"""

    return common + """

For this run the evolution scope is FULL.

You may modify relevant parts of the agent implementation and workflow when
that is justified by the evaluation.

Preserve the ability to execute the experiment and do not alter evaluation
results merely to improve the score.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument(
        "--scope",
        choices=["prompt", "full"],
        default="prompt",
    )
    args = parser.parse_args()

    report_file = (
        ROOT_DIR
        / "outputs"
        / "prompt_design"
        / f"gen_{args.generation:03d}"
        / "report.json"
    )

    report = json.loads(
        report_file.read_text(encoding="utf-8")
    )

    instruction = build_instruction(
        report=report,
        generation=args.generation,
        scope=args.scope,
    )

    with usage_context(
        agent_role="meta_agent",
        metadata={
            "domain": "prompt_design",
            "generation": args.generation,
            "scope": args.scope,
        },
    ):
        chat_with_agent(
            msg=instruction,
            model=get_configured_model("meta_agent", CLAUDE_HAIKU_45_MODEL),
            tools_available="all",
            max_tool_calls=20,
        )


if __name__ == "__main__":
    main()
