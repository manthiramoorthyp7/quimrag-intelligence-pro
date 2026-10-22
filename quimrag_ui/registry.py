"""Single source of truth for 'Research Gaps & Validation' status, read by
both the Command Center and the Research Gaps page so the two never diverge.
research/experiments/registry.json is updated by the gap-closing scripts
themselves (research/run_*.py) as each study actually completes -- nothing
here is hand-typed to look finished."""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(ROOT, "research", "experiments", "registry.json")
EXPERIMENTS_DIR = os.path.join(ROOT, "research", "experiments")


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        return {"gaps": []}
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def save_registry(data):
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def update_gap(gap_id, **fields):
    data = load_registry()
    found = False
    for g in data["gaps"]:
        if g["id"] == gap_id:
            g.update(fields)
            found = True
            break
    if not found:
        raise KeyError(f"Unknown gap id: {gap_id}")
    save_registry(data)
    return data


def list_experiment_runs():
    """-> sorted list of (run_id, path) for every logged research/experiments/*.json run,
    excluding the registry file itself."""
    paths = sorted(glob.glob(os.path.join(EXPERIMENTS_DIR, "*.json")))
    out = []
    for p in paths:
        name = os.path.basename(p)
        if name == "registry.json":
            continue
        out.append((name.replace(".json", ""), p))
    return out


def load_latest_benchmark_run():
    """-> parsed dict of the most recent research/run_benchmark.py output, or None."""
    runs = [r for r in list_experiment_runs() if r[0][0].isdigit()]
    if not runs:
        return None
    run_id, path = sorted(runs, key=lambda x: x[0])[-1]
    with open(path) as f:
        return json.load(f)


def load_latest_run(prefix):
    """-> parsed dict of the most recent research/experiments/<prefix>_*.json
    (a bare summary JSON, not a *_per_query.csv), or None."""
    runs = [r for r in list_experiment_runs() if r[0].startswith(prefix)]
    if not runs:
        return None
    run_id, path = sorted(runs, key=lambda x: x[0])[-1]
    with open(path) as f:
        return json.load(f)
