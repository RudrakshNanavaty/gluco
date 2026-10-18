"""Fixed uncalibrated margin-to-score transform; no fitting or calibration."""

import numpy as np


def margin_scores(margins):
    margins = np.asarray(margins, dtype=float)
    if not np.isfinite(margins).all():
        raise ValueError("Decision margins must be finite")
    return np.exp(-np.logaddexp(0, -margins))
