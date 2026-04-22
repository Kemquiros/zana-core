//! ZANA Steel Core: EML Symbolic Engine
//! Implementation of the Exp-Minus-Log operator for maximum precision.

/// The EML (Exp-Minus-Log) operator.
/// eml(x, y) = exp(x) - ln(y)
pub fn eml(x: f64, y: f64) -> f64 {
    // Safety check for log domain
    let y_safe = if y <= 0.0 { 1e-10 } else { y };
    x.exp() - y_safe.ln()
}

/// Reconstructs e^x using EML basis.
pub fn exp_eml(x: f64) -> f64 {
    eml(x, 1.0)
}

/// Reconstructs ln(x) using EML basis.
pub fn log_eml(x: f64) -> f64 {
    eml(1.0, eml(eml(1.0, x), 1.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_eml_precision() {
        let val: f64 = 2.0;
        let expected = val.ln();
        let actual = log_eml(val);
        assert!((expected - actual).abs() < 1e-15);
    }
}
