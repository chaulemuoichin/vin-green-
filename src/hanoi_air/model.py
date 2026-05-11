from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover - exercised when torch is unavailable
    torch = None  # type: ignore
    nn = None  # type: ignore


def make_supervised_sequences(
    values: np.ndarray, lookback: int = 24, horizon: int = 24
) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(values, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr[:, None]
    if len(arr) < lookback + horizon:
        raise ValueError("Not enough rows to build supervised sequences")
    x_rows = []
    y_rows = []
    for start in range(0, len(arr) - lookback - horizon + 1):
        x_rows.append(arr[start : start + lookback])
        y_rows.append(arr[start + lookback : start + lookback + horizon, 0])
    return np.stack(x_rows), np.stack(y_rows)


if torch is not None:

    class _TorchLSTM(nn.Module):  # type: ignore[misc]
        def __init__(self, input_size: int, hidden_size: int, horizon: int) -> None:
            super().__init__()
            self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
            self.head = nn.Linear(hidden_size, horizon)

        def forward(self, x):  # type: ignore[no-untyped-def]
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :])


@dataclass
class LSTMForecaster:
    input_size: int = 1
    hidden_size: int = 16
    horizon: int = 24
    seed: int = 7

    def __post_init__(self) -> None:
        self._fallback_mean_delta = 0.0
        self._model: object | None = None
        if torch is not None:
            torch.manual_seed(self.seed)
            self._model = _TorchLSTM(self.input_size, self.hidden_size, self.horizon)

    @property
    def using_torch(self) -> bool:
        return self._model is not None and torch is not None

    def fit(
        self, x: np.ndarray, y: np.ndarray, epochs: int = 5, lr: float = 0.01
    ) -> LSTMForecaster:
        x = np.asarray(x, dtype=np.float32)
        y = np.asarray(y, dtype=np.float32)
        if self.using_torch:
            assert torch is not None
            model = self._model
            assert model is not None
            optimizer = torch.optim.Adam(model.parameters(), lr=lr)  # type: ignore[union-attr]
            loss_fn = torch.nn.MSELoss()
            x_t = torch.tensor(x, dtype=torch.float32)
            y_t = torch.tensor(y, dtype=torch.float32)
            model.train()  # type: ignore[attr-defined]
            for _ in range(max(1, epochs)):
                optimizer.zero_grad()
                pred = model(x_t)  # type: ignore[operator]
                loss = loss_fn(pred, y_t)
                loss.backward()
                optimizer.step()
        else:
            last_values = x[:, -1, 0]
            self._fallback_mean_delta = float(
                np.mean(y[:, -1] - last_values) / max(1, self.horizon)
            )
        return self

    def predict(self, x_last: np.ndarray) -> np.ndarray:
        x_last = np.asarray(x_last, dtype=np.float32)
        if x_last.ndim == 2:
            x_last = x_last[None, :, :]
        if self.using_torch:
            assert torch is not None
            model = self._model
            assert model is not None
            model.eval()  # type: ignore[attr-defined]
            with torch.no_grad():
                pred = model(torch.tensor(x_last, dtype=torch.float32))  # type: ignore[operator]
            return pred.detach().cpu().numpy()[0]
        last = float(x_last[0, -1, 0])
        return np.array(
            [max(0.0, last + self._fallback_mean_delta * (i + 1)) for i in range(self.horizon)],
            dtype=np.float32,
        )


def synthetic_training_matrix(length: int = 96, base: float = 42.0, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    hours = np.arange(length)
    diurnal = 6.0 * np.sin((hours - 7) / 24.0 * 2.0 * np.pi)
    winter_bias = np.where((hours // 24) % 4 == 0, 5.0, 0.0)
    noise = rng.normal(0.0, 1.5, size=length)
    pm25 = np.maximum(8.0, base + diurnal + winter_bias + noise)
    wind_speed = 2.5 + 0.6 * np.sin(hours / 24.0 * 2.0 * np.pi)
    humidity = 72.0 + 8.0 * np.cos(hours / 24.0 * 2.0 * np.pi)
    return np.column_stack([pm25, wind_speed, humidity]).astype(np.float32)
