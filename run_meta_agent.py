import argparse
import os

from agent.config import get_configured_model
from agent.llm import CLAUDE_MODEL
from meta_agent import MetaAgent
from utils.git_utils import diff_versus_commit, reset_paths_to_commit


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        type=str,
        default=get_configured_model("meta_agent", CLAUDE_MODEL),
        help="Model to use for the agent. Defaults to models.meta_agent from hyperagent_config.json.",
    )
    parser.add_argument(
        "--chat_history_file",
        type=str,
        default="./outputs/chat_history.md",
        help="Path to chat history file",
    )
    parser.add_argument(
        "--repo_path", type=str, default="./", help="Path to the agent file"
    )
    parser.add_argument(
        "--evals_folder",
        type=str,
        default="./outputs/",
        help="Path to the folder containing the evaluation files",
    )
    parser.add_argument(
        "--iterations_left",
        type=int,
        default=None,
        help="The number of remaining iterations in which the meta agent will be invoked in future.",
    )
    parser.add_argument(
        "--git_dir", required=True, help="Path to git repository directory"
    )
    parser.add_argument(
        "--base_commit", required=True, help="Base commit hash to compare against"
    )
    parser.add_argument(
        "--outdir", required=False, default="./outputs/", help="Output directory"
    )
    args = parser.parse_args()

    # Run meta agent
    meta_agent = MetaAgent(
        model=args.model,
        chat_history_file=args.chat_history_file,
    )
    meta_agent.forward(
        repo_path=args.repo_path,
        eval_path=args.evals_folder,
        iterations_left=args.iterations_left,
    )

    # Reset unwanted diffs
    reset_paths_to_commit(
        git_dname=args.git_dir, commit=args.base_commit, paths=["domains/"]
    )

    # Save git diff
    model_patch = diff_versus_commit(args.git_dir, args.base_commit)
    model_patch_outfile = (
        os.path.join(args.outdir, "model_patch.diff")
        if args.outdir
        else "model_patch.diff"
    )
    with open(model_patch_outfile, "w") as f:
        f.write(model_patch)


if __name__ == "__main__":
    main()
