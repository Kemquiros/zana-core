import numpy as np
from typing import Union
import xana_steel_core

def eml(x: Union[float, np.ndarray], y: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    XANA Steel Core Wrapper for EML (Rust implementation).
    eml(x, y) = exp(x) - ln(y)
    """
    if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
        # For vectorized arrays, we use the original numpy for now or map.
        # Since Rust implementation is scalar, we vectorize it here.
        func = np.vectorize(xana_steel_core.eml_op)
        return func(x, y)
    return xana_steel_core.eml_op(x, y)

def eml_op(x: float, y: float) -> float:
    return xana_steel_core.eml_op(x, y)

def exp_eml(x: float) -> float:
    return xana_steel_core.exp_eml(x)

def log_eml(x: float) -> float:
    return xana_steel_core.log_eml(x)

# Reconstructions maintained for backward compatibility
def constant_e():
    return xana_steel_core.exp_eml(1.0)
