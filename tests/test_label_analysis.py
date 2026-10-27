"""The rating-study analysis must reproduce the JS analysis output exactly."""

import importlib.util
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parents[1] / "study" / "analysis" / "label_analysis.py"


def test_label_analysis_matches_reference_output(fixtures_dir, capsys):
    spec = importlib.util.spec_from_file_location("label_analysis", ANALYSIS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    assert capsys.readouterr().out == (fixtures_dir / "expected_label_analysis.txt").read_text()
