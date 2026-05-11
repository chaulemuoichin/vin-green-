import numpy as np

from hanoi_air.model import LSTMForecaster, make_supervised_sequences, synthetic_training_matrix


def test_make_supervised_sequences_shapes():
    matrix = synthetic_training_matrix(length=60)
    x, y = make_supervised_sequences(matrix, lookback=12, horizon=6)
    assert x.shape == (43, 12, 3)
    assert y.shape == (43, 6)


def test_lstm_forecaster_smoke_predicts_horizon():
    matrix = synthetic_training_matrix(length=80)
    x, y = make_supervised_sequences(matrix, lookback=12, horizon=6)
    model = LSTMForecaster(input_size=3, hidden_size=6, horizon=6, seed=1)
    model.fit(x[:16], y[:16], epochs=1)
    pred = model.predict(x[-1])
    assert pred.shape == (6,)
    assert np.isfinite(pred).all()
