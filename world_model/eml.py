
import numpy as np
import zana_steel_core


def eml(
    x: float | np.ndarray, y: float | np.ndarray
) -> float | np.ndarray:
    """
    ZANA Steel Core Wrapper for EML (Rust implementation).
    eml(x, y) = exp(x) - ln(y)
    """
    if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
        # For vectorized arrays, we use the original numpy for now or map.
        # Since Rust implementation is scalar, we vectorize it here.
        func = np.vectorize(zana_steel_core.eml_op)
        return func(x, y)
    return zana_steel_core.eml_op(x, y)


def eml_op(x: float, y: float) -> float:
    return zana_steel_core.eml_op(x, y)


def exp_eml(x: float | np.ndarray) -> float | np.ndarray:
    if isinstance(x, np.ndarray):
        func = np.vectorize(zana_steel_core.exp_eml)
        return func(x)
    return zana_steel_core.exp_eml(x)


def log_eml(x: float | np.ndarray) -> float | np.ndarray:
    if isinstance(x, np.ndarray):
        func = np.vectorize(zana_steel_core.log_eml)
        return func(x)
    return zana_steel_core.log_eml(x)


# Reconstructions maintained for backward compatibility
def constant_e():
    return zana_steel_core.exp_eml(1.0)
