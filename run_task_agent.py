import argparse
import os

from agent.config import get_configured_model
from task_agent import TaskAgent
from utils.git_utils import diff_versus_commit


def main():
    parser = argparse.ArgumentParser(description='Run task agent on POLYGLOT benchmark.')
    parser.add_argument('--problem_statement', required=True, help='The problem statement to process')
    parser.add_argument('--git_dir', required=True, help='Path to git repository directory')
    parser.add_argument('--base_commit', required=True, help='Base commit hash to compare against')
    parser.add_argument('--chat_history_file', required=True, help='Path to chat history file')
    parser.add_argument('--outdir', required=False, default="/dgm/", help='Output directory')
    parser.add_argument('--test_description', default=None, required=False, help='Description of how to test the repository')
    parser.add_argument('--language', default=None, required=False, help='Coding language of the repository')
    parser.add_argument('--model', required=False, default=get_configured_model("task_agent", "o3-mini"), help='LLM model to use. Defaults to models.task_agent from hyperagent_config.json.')
    args = parser.parse_args()

    # Process the repository
    agentic_system = TaskAgent(
        model=args.model,
        chat_history_file=args.chat_history_file,
    )
    inputs = {
        "domain": "polyglot",
        "problem_statement": args.problem_statement,
        "git_tempdir": args.git_dir,
        "base_commit": args.base_commit,
        "test_description": args.test_description,
        "language": args.language,
    }

    # Run the agentic system to try to solve the problem
    agentic_system.forward(inputs)

    # Get code diff and save to model_patch.diff
    model_patch = diff_versus_commit(args.git_dir, args.base_commit)
    model_patch_outfile = os.path.join(args.outdir, 'model_patch.diff') if args.outdir else 'model_patch.diff'
    with open(model_patch_outfile, 'w') as f:
        f.write(model_patch)

if __name__ == "__main__":
    main()
