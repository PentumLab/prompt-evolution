import argparse
import json
import py_compile
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from domains.prompt_design.evolution_state import (
    create_patch,
    generation_dir,
    rebuild_archive,
    restore_agent,
    save_metadata,
    select_parent,
    snapshot_agent,
    validate_meta_generation,
)


def build_instruction(report, source_generation, target_generation, scope, workspace_dir):
    target_file = ROOT_DIR / "prompt_design_agent.py"
    source_prompt_file = ROOT_DIR / "domains" / "prompt_design" / "prompt.md"
    guidance_file = ROOT_DIR / "domains" / "prompt_design" / "guidance.md"
    previous_generation_dir = generation_dir(source_generation)

    common = f"""
You are improving the prompt-generation strategy for Prompt Evolution.

Parent generation:
gen_{source_generation:03d}

Target generation:
gen_{target_generation:03d}

Latest evaluation:

Overall score: {report["score"]}/100
Methodology: {report["methodology"]}/25
Consistency: {report["consistency"]}/25
Robustness: {report["robustness"]}/25
Efficiency: {report["efficiency"]}/25

Human feedback:
{report["feedback"]}

The evaluation and task context needed for this run are included here. Use the
parent generation artifacts when they help you understand what the current
agent produced and how it was evaluated.

This domain improves an existing source prompt instead of designing a prompt
from scratch. The generator should preserve the source prompt's core purpose
while improving clarity, robustness, operational rules, and consistency.

You may read:
- {target_file}
- {source_prompt_file}
- {guidance_file}
- files inside {previous_generation_dir}
- files inside {workspace_dir}

You may edit:
- {target_file}

You may freely create, edit, and remove files inside:
- {workspace_dir}

If you want to reinterpret, summarize, or adapt the task for this run, write
that as a new artifact inside the workspace. Keep the source prompt, guidance
file, and all evaluation/report files unchanged.

Make an actual code change to {target_file}. Do not merely describe changes.

TOOL PROTOCOL:
- Use exactly ONE tool per response.
- Tool calls MUST use exactly this format:

<json>
{{
    "tool_name": "...",
    "tool_input": {{...}}
}}
</json>

- Never use <function_calls>, <invoke_tool>, XML tool calls, or any other
  tool-call syntax.
- Never simulate a tool result.
- Wait for the real tool result before making the next tool call.

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

Workspace:
{workspace_dir}

STRICT CONSTRAINTS:
- Preserve generate_prompt(task: str) -> str.
- It must continue to return a Python string.
- Keep the existing single Task-Agent LLM call.
- Do not add runtime evaluator logic or extra model calls.
- Improve the prompt-generation strategy inside generate_prompt().
- Preserve the behavior that the Task-Agent improves an existing prompt and
  does not replace it with an unrelated prompt.

IMPLEMENTATION PROTOCOL:
- Make exactly one small but meaningful improvement.
- First use editor view on the target file.
- Then use editor str_replace on a short exact substring copied verbatim from
  the file you viewed.
- Prioritize the actual edit before exploration or documentation. Do not list
  directories or create notes, reports, checklists, or summaries before editing.
- If an edit fails, use the real error and file contents to fix that edit next.
- Never assume a proposed tool call was executed. Only real tool results prove
  that a change or validation happened.
- Do not replace the whole function or whole file.
- Do not use sed.
- After the edit, view the file again.
- Then run py_compile.
- Only after the edit and validation succeed may you write optional workspace
  documentation. Documentation is not required; prefer finishing immediately
  with a short plain-text summary. Do not spend tools printing success messages.
- Reserve remaining tool calls for the edit, verification, and necessary fixes.
- Do not finish unless the target file actually changed.

SUGGESTED TOOL CYCLE:
1. editor view
2. editor str_replace
3. editor view to verify the real change
4. bash py_compile
5. finish with a short plain-text summary (no tool call)
"""

    return common + """

For this run the evolution scope is FULL.

You may modify relevant parts of the agent implementation and workflow when
that is justified by the evaluation.

Preserve the ability to execute the experiment and do not alter evaluation
results merely to improve the score.
"""


def build_logger(log_file, append=False):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not append:
        log_file.write_text("", encoding="utf-8")

    def log(message):
        text = str(message)
        print(text)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")

    return log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, default=None)
    parser.add_argument("--target-generation", type=int, default=None)
    parser.add_argument(
        "--parent-selection",
        choices=["best", "latest", "random", "score_prop", "score_child_prop"],
        default=None,
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--scope",
        choices=["prompt", "full"],
        default="prompt",
    )
    args = parser.parse_args()
    if args.scope != "prompt":
        parser.error(
            "--scope full is not supported by the prompt_design mini-loop yet. "
            "Use --scope prompt."
        )

    from agent.config import (
        get_agent_max_output_tokens,
        get_agent_max_tool_calls,
        get_configured_model,
    )
    from agent.llm import CLAUDE_HAIKU_45_MODEL
    from agent.llm_withtools import chat_with_agent
    from agent.usage import usage_context

    source_generation = args.generation
    if args.parent_selection:
        source_generation = select_parent(args.parent_selection)
    if source_generation is None:
        parser.error("Either --generation or --parent-selection is required.")
    target_generation = (
        args.target_generation
        if args.target_generation is not None
        else source_generation + 1
    )

    target_dir = generation_dir(target_generation)
    if target_dir.exists() and any(target_dir.iterdir()) and not args.force and not args.resume:
        parser.error(
            f"{target_dir} already exists. Use --force to overwrite this "
            "target generation."
        )
    workspace_dir = target_dir / "meta_workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    pre_restore_backup = target_dir / "pre_restore_prompt_design_agent.py"
    if not args.resume and (ROOT_DIR / "prompt_design_agent.py").exists():
        shutil.copyfile(ROOT_DIR / "prompt_design_agent.py", pre_restore_backup)
    if not args.resume:
        restore_agent(source_generation)

    report_file = (
        ROOT_DIR
        / "outputs"
        / "prompt_design"
        / f"gen_{source_generation:03d}"
        / "report.json"
    )

    report = json.loads(
        report_file.read_text(encoding="utf-8")
    )

    instruction = build_instruction(
        report=report,
        source_generation=source_generation,
        target_generation=target_generation,
        scope=args.scope,
        workspace_dir=workspace_dir,
    )

    log_file = target_dir / "meta_agent_chat_history.md"
    log = build_logger(log_file, append=args.resume)
    resume_state_file = target_dir / "meta_agent_resume_state.json"

    try:
        with usage_context(
            agent_role="meta_agent",
            metadata={
                "domain": "prompt_design",
                "source_generation": source_generation,
                "target_generation": target_generation,
                "scope": args.scope,
            },
        ):
            chat_with_agent(
                msg=instruction,
                model=get_configured_model("meta_agent", CLAUDE_HAIKU_45_MODEL),
                logging=log,
                tools_available=["editor", "bash"],
                max_tool_calls=get_agent_max_tool_calls("meta_agent"),
                max_tokens=get_agent_max_output_tokens("meta_agent"),
                resume_state_file=resume_state_file,
                resume=args.resume,
            )
    except Exception as exc:
        save_metadata(
            target_generation,
            {
                "parent_genid": source_generation,
                "source_generation": source_generation,
                "target_generation": target_generation,
                "scope": args.scope,
                "meta_agent_chat_history": str(log_file),
                "meta_workspace": str(workspace_dir),
                "pre_restore_backup": str(pre_restore_backup),
                "resume_state": str(resume_state_file),
                "valid_parent": False,
                "status": "interrupted",
                "error": str(exc),
            },
        )
        rebuild_archive()
        print(f"Run interrupted. Resume state written to: {resume_state_file}")
        raise
    py_compile.compile(str(ROOT_DIR / "prompt_design_agent.py"), doraise=True)
    snapshot_file = snapshot_agent(target_generation)
    patch_file = create_patch(source_generation, target_generation)
    validation_errors = validate_meta_generation(source_generation, target_generation)
    if validation_errors:
        save_metadata(
            target_generation,
            {
                "parent_genid": source_generation,
                "source_generation": source_generation,
                "target_generation": target_generation,
                "scope": args.scope,
                "agent_snapshot": str(snapshot_file),
                "curr_patch_files": [str(patch_file)],
                "meta_agent_chat_history": str(log_file),
                "meta_workspace": str(workspace_dir),
                "pre_restore_backup": str(pre_restore_backup),
                "resume_state": str(resume_state_file),
                "valid_parent": False,
                "validation_errors": validation_errors,
                "error": "; ".join(validation_errors),
                "status": "failed",
            },
        )
        rebuild_archive()
        print("Run validation failed:")
        for error in validation_errors:
            print(f"- {error}")
        sys.exit(1)
    save_metadata(
        target_generation,
        {
            "parent_genid": source_generation,
            "source_generation": source_generation,
            "target_generation": target_generation,
            "scope": args.scope,
            "agent_snapshot": str(snapshot_file),
            "curr_patch_files": [str(patch_file)],
            "meta_agent_chat_history": str(log_file),
            "meta_workspace": str(workspace_dir),
            "pre_restore_backup": str(pre_restore_backup),
            "resume_state": str(resume_state_file),
            "valid_parent": False,
            "status": "pending_evaluation",
        },
    )
    rebuild_archive()
    print(f"Parent generation: gen_{source_generation:03d}")
    print(f"Target generation: gen_{target_generation:03d}")
    print(f"Agent snapshot written to: {snapshot_file}")
    print(f"Patch written to: {patch_file}")


if __name__ == "__main__":
    main()
