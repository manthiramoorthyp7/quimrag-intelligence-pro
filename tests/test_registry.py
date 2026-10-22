import json

from quimrag_ui import registry as R


def test_load_registry_reads_real_file():
    data = R.load_registry()
    assert "gaps" in data
    assert len(data["gaps"]) == 5
    ids = {g["id"] for g in data["gaps"]}
    assert ids == {
        "ndsu_reproduction", "ocr_robustness", "generation_quality", "rvq_recall",
        "final_validation_ear_core_claim",
    }


def test_all_gaps_have_required_fields():
    data = R.load_registry()
    required = {"id", "title", "problem_statement", "status", "baseline", "proposed",
                "results", "report_path"}
    for g in data["gaps"]:
        assert required <= set(g), f"{g['id']} missing fields"


def test_update_gap_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"gaps": [{"id": "x", "status": "not_started"}]}))
    monkeypatch.setattr(R, "REGISTRY_PATH", str(path))
    R.update_gap("x", status="done", sample_count=42)
    data = R.load_registry()
    assert data["gaps"][0]["status"] == "done"
    assert data["gaps"][0]["sample_count"] == 42


def test_update_gap_unknown_id_raises(tmp_path, monkeypatch):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"gaps": [{"id": "x"}]}))
    monkeypatch.setattr(R, "REGISTRY_PATH", str(path))
    try:
        R.update_gap("does_not_exist", status="done")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_list_experiment_runs_excludes_registry_itself():
    runs = R.list_experiment_runs()
    names = {name for name, _ in runs}
    assert "registry" not in names
