"""Split-conformal intervals around a clear-sky PV shape."""

from __future__ import annotations

from sklearn.base import BaseEstimator, RegressorMixin


class ScaledClearsky(BaseEstimator, RegressorMixin):
    """Multiply the 1 kW clear-sky shape by one scale learned from recorded PV."""

    def fit(self, features, measured):
        import numpy as np

        shape = np.asarray(features, dtype=float)[:, 0]
        target = np.asarray(measured, dtype=float)
        usable = shape > 0.02
        self.scale_ = (
            float(np.median(target[usable] / shape[usable])) if int(usable.sum()) >= 8 else 1.0
        )
        self.n_features_in_ = int(np.asarray(features).shape[1])
        return self

    def predict(self, features):
        import numpy as np

        shape = np.asarray(features, dtype=float)[:, 0]
        return np.clip(shape * self.scale_, 0, None)


def intervals(features: list[list[float]], measured: list[float], queries: list[list[float]]) -> dict:
    """80% intervals. The first 70% of rows fit the scale; the last 30% calibrate it."""
    import numpy as np
    from mapie.regression import SplitConformalRegressor

    count = len(measured)
    split = max(8, int(count * 0.7))
    if count < 24 or count - split < 8:
        return {"calibrated": False, "scale": None, "point_kw": None, "lower_kw": None, "upper_kw": None}
    features_array = np.asarray(features, dtype=float)
    measured_array = np.asarray(measured, dtype=float)
    estimator = ScaledClearsky().fit(features_array[:split], measured_array[:split])
    model = SplitConformalRegressor(estimator, confidence_level=0.8, prefit=True)
    model.conformalize(features_array[split:], measured_array[split:])
    point, bounds = model.predict_interval(np.asarray(queries, dtype=float))
    return {
        "calibrated": True,
        "scale": round(float(estimator.scale_), 4),
        "point_kw": [round(float(value), 3) for value in point],
        "lower_kw": [round(float(value), 3) for value in bounds[:, 0, 0]],
        "upper_kw": [round(float(value), 3) for value in bounds[:, 1, 0]],
    }
