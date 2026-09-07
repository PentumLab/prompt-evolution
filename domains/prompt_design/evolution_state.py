import difflib
import json
import py_compile
import random
import shutil
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "outputs" / "prompt_design"
ARCHIVE_FILE = OUTPUT_DIR / "archive.jsonl"
AGENT_FILE = ROOT_DIR / "prompt_design_agent.py"
SNAPSHOT_FILE = "prompt_design_agent.py"
PATCH_FILE = "model_patch.diff"


def generation_dir(generation):
    return OUTPUT_DIR / f"gen_{int(generation):03d}"


def generation_ids():
    if not OUTPUT_DIR.exists():
        return []

    ids = []
    for path in OUTPUT_DIR.glob("gen_[0-9][0-9][0-9]"):
        try:
            ids.append(int(path.name.split("_", 1)[1]))
        except ValueError:
            continue
    return sorted(ids)


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def snapshot_path(generation):
    return generation_dir(generation) / SNAPSHOT_FILE


def has_snapshot(generation):
    return snapshot_path(generation).exists()


def snapshot_agent(generation):
    out = snapshot_path(generation)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(AGENT_FILE, out)
    return out


def restore_agent(generation):
    source = snapshot_path(generation)
    if not source.exists():
        raise FileNotFoundError(
            f"Missing agent snapshot for gen_{int(generation):03d}: {source}"
        )
    shutil.copyfile(source, AGENT_FILE)
    return AGENT_FILE


def report_score(generation):
    report = read_json(generation_dir(generation) / "report.json", default={})
    if not report:
        return None
    if "overall_score" in report:
        return float(report["overall_score"])
    if "score" in report:
        return float(report["score"]) / 100.0
    return None


def metadata_path(generation):
    return generation_dir(generation) / "metadata.json"


def load_metadata(generation):
    return read_json(metadata_path(generation), default={}) or {}


def save_metadata(generation, updates):
    metadata = load_metadata(generation)
    metadata.update(updates)
    metadata.setdefault("generation", int(generation))
    write_json(metadata_path(generation), metadata)
    return metadata


def evaluated_generations():
    result = []
    for generation in generation_ids():
        metadata = load_metadata(generation)
        score = report_score(generation)
        if score is None or not has_snapshot(generation):
            continue
        if metadata.get("valid_parent", True) is False:
            continue
        result.append(generation)
    return result


def child_counts(candidates):
    counts = {generation: 0 for generation in candidates}
    for generation in generation_ids():
        parent = load_metadata(generation).get("parent_genid")
        if parent in counts:
            counts[parent] += 1
    return counts


def select_parent(method="best"):
    candidates = evaluated_generations()
    if not candidates:
        raise ValueError(
            "No evaluated parent generation found. Run harness.py and "
            "manual_evaluator.py for at least one generation first."
        )

    scores = {generation: report_score(generation) for generation in candidates}

    if method == "latest":
        return candidates[-1]
    if method == "best":
        return max(candidates, key=lambda generation: scores[generation])
    if method == "random":
        return random.choice(candidates)
    if method in {"score_prop", "score_child_prop"}:
        counts = child_counts(candidates)
        weights = []
        for generation in candidates:
            score = max(scores[generation] or 0.0, 0.0)
            weight = score + 0.01
            if method == "score_child_prop":
                weight = weight / (1 + counts[generation])
            weights.append(weight)
        return random.choices(candidates, weights=weights, k=1)[0]

    raise ValueError(f"Unknown parent selection method: {method}")


def next_generation_id():
    ids = generation_ids()
    return 0 if not ids else ids[-1] + 1


def create_patch(parent_generation, target_generation):
    parent_file = snapshot_path(parent_generation)
    target_file = snapshot_path(target_generation)
    if not parent_file.exists():
        raise FileNotFoundError(f"Missing parent snapshot: {parent_file}")
    if not target_file.exists():
        raise FileNotFoundError(f"Missing target snapshot: {target_file}")

    old_lines = parent_file.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = target_file.read_text(encoding="utf-8").splitlines(keepends=True)
    patch = "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="a/prompt_design_agent.py",
            tofile="b/prompt_design_agent.py",
        )
    )

    patch_path = generation_dir(target_generation) / PATCH_FILE
    patch_path.write_text(patch, encoding="utf-8")
    return patch_path


def validate_meta_generation(parent_generation, target_generation):
    errors = []
    parent_file = snapshot_path(parent_generation)
    target_file = snapshot_path(target_generation)
    patch_file = generation_dir(target_generation) / PATCH_FILE

    if not parent_file.exists():
        errors.append(f"Missing parent snapshot: {parent_file}")
    if not target_file.exists():
        errors.append(f"Missing target snapshot: {target_file}")

    if target_file.exists():
        try:
            py_compile.compile(str(target_file), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"Target snapshot does not compile: {exc}")

    if parent_file.exists() and target_file.exists():
        if parent_file.read_bytes() == target_file.read_bytes():
            errors.append("Meta-Agent did not change prompt_design_agent.py")

    if not patch_file.exists():
        errors.append(f"Missing patch file: {patch_file}")
    elif not patch_file.read_text(encoding="utf-8").strip():
        errors.append(f"Patch file is empty: {patch_file}")

    return errors


def rebuild_archive():
    archive = []
    for generation in generation_ids():
        metadata = load_metadata(generation)
        if has_snapshot(generation) or metadata:
            archive.append(generation)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_FILE.write_text("", encoding="utf-8")
    current = []
    with ARCHIVE_FILE.open("a", encoding="utf-8") as handle:
        for generation in archive:
            current.append(generation)
            handle.write(
                json.dumps(
                    {
                        "current_genid": generation,
                        "archive": current.copy(),
                    },
                    ensure_ascii=False,
                )
            )
            handle.write("\n")
    return archive
