from sunset import cli


def test_scenarios_output_matches_the_original(fixtures_dir, capsys):
    assert cli.main(["scenarios"]) == 0
    assert capsys.readouterr().out == (fixtures_dir / "expected_scenarios.txt").read_text()
