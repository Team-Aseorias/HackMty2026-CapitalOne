from app.ml.simulator import generate_synthetic_data


def test_simulator_generates_requested_rows() -> None:
    assert len(generate_synthetic_data(2)) == 2
