"""Validation for model-produced prompt-design evaluations."""

REQUIRED_COMPONENTS = ("methodology", "consistency", "robustness", "efficiency")


def validate_evaluation(data):
    if not isinstance(data, dict):
        raise ValueError("Evaluator response must be a JSON object")
    missing = [key for key in ("score", *REQUIRED_COMPONENTS, "feedback") if key not in data]
    if missing:
        raise ValueError(f"Missing evaluator fields: {', '.join(missing)}")
    values = [data[key] for key in REQUIRED_COMPONENTS]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 25 for value in values):
        raise ValueError("Each component score must be a number between 0 and 25")
    if isinstance(data["score"], bool) or not isinstance(data["score"], (int, float)):
        raise ValueError("score must be numeric")
    if sum(values) != data["score"]:
        raise ValueError("score must equal the sum of the component scores")
    if not isinstance(data["feedback"], str) or not data["feedback"].strip():
        raise ValueError("feedback must be a non-empty string")
    return data
