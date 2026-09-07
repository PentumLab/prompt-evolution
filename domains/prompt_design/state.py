import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from domains.prompt_design.evolution_state import (
    create_patch,
    evaluated_generations,
    generation_dir,
    generation_ids,
    has_snapshot,
    load_metadata,
    rebuild_archive,
    report_score,
    restore_agent,
    save_metadata,
    select_parent,
    snapshot_agent,
    snapshot_path,
    validate_meta_generation,
)


def print_status():
    generations = generation_ids()
    if not generations:
        print("No prompt_design generations found.")
        return

    print("Generation status:")
    for generation in generations:
        metadata = load_metadata(generation)
        score = report_score(generation)
        parent = metadata.get("parent_genid")
        status = metadata.get("status", "-")
        valid_parent = generation in evaluated_generations()
        snapshot = "yes" if has_snapshot(generation) else "no"
        score_text = "-" if score is None else f"{score:.3f}"
        parent_text = "-" if parent is None else f"gen_{parent:03d}"
        valid_text = "yes" if valid_parent else "no"
        print(
            f"gen_{generation:03d}  "
            f"score={score_text}  "
            f"parent={parent_text}  "
            f"snapshot={snapshot}  "
            f"status={status}  "
            f"selectable_parent={valid_text}"
        )


def main():
    parser = argparse.ArgumentParser(description="Manage Prompt Evolution state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")
    subparsers.add_parser("rebuild-archive")

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--generation", type=int, required=True)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--generation", type=int, required=True)

    parent_parser = subparsers.add_parser("select-parent")
    parent_parser.add_argument(
        "--method",
        choices=["best", "latest", "random", "score_prop", "score_child_prop"],
        default="best",
    )

    patch_parser = subparsers.add_parser("create-patch")
    patch_parser.add_argument("--parent-generation", type=int, required=True)
    patch_parser.add_argument("--target-generation", type=int, required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--generation", type=int, required=True)
    validate_parser.add_argument("--parent-generation", type=int, default=None)

    args = parser.parse_args()

    if args.command == "status":
        print_status()
    elif args.command == "snapshot":
        path = snapshot_agent(args.generation)
        save_metadata(
            args.generation,
            {
                "agent_snapshot": str(snapshot_path(args.generation)),
            },
        )
        rebuild_archive()
        print(f"Snapshot written to: {path}")
    elif args.command == "restore":
        path = restore_agent(args.generation)
        print(f"Restored gen_{args.generation:03d} to: {path}")
    elif args.command == "select-parent":
        generation = select_parent(args.method)
        print(f"gen_{generation:03d}")
    elif args.command == "create-patch":
        path = create_patch(args.parent_generation, args.target_generation)
        save_metadata(
            args.target_generation,
            {
                "parent_genid": args.parent_generation,
                "curr_patch_files": [str(path)],
            },
        )
        rebuild_archive()
        print(f"Patch written to: {path}")
    elif args.command == "validate":
        metadata = load_metadata(args.generation)
        parent_generation = args.parent_generation
        if parent_generation is None:
            parent_generation = metadata.get("parent_genid")
        if parent_generation is None:
            parser.error(
                "--parent-generation is required when metadata has no parent_genid."
            )
        errors = validate_meta_generation(parent_generation, args.generation)
        if errors:
            print(f"Validation failed for gen_{args.generation:03d}:")
            for error in errors:
                print(f"- {error}")
            sys.exit(1)
        print(f"Validation passed for gen_{args.generation:03d}.")
    elif args.command == "rebuild-archive":
        archive = rebuild_archive()
        print("Archive rebuilt:")
        for generation in archive:
            print(f"- {generation_dir(generation).name}")


if __name__ == "__main__":
    main()
