//! ZANA Steel Core: Cognitive Kalman Filter
//! Optimized linear algebra for Bayesian surprise detection.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FilterMode {
    Precision,
    Adaptability,
    Temporal,
    Hybrid,
}

pub struct CognitiveKalmanFilter {
    pub dim: usize,
    pub state: Vec<f64>,
    pub uncertainty: Vec<f64>, // Flattened diagonal for simplicity in this prototype
    pub q: f64, // Process noise
    pub r: f64, // Measurement noise
    pub mode: FilterMode,
}

impl CognitiveKalmanFilter {
    pub fn new(dim: usize, q: f64, r: f64) -> Self {
        Self::with_mode(dim, q, r, FilterMode::Adaptability)
    }

    pub fn with_mode(dim: usize, q: f64, r: f64, mode: FilterMode) -> Self {
        Self {
            dim,
            state: vec![0.0; dim],
            uncertainty: vec![1.0; dim], // Initial high uncertainty
            q,
            r,
            mode,
        }
    }

    /// Update state with new observation and return Bayesian Surprise.
    ///
    /// The loop is structured for auto-vectorization: all slices are independent
    /// per-element, no loop-carried dependencies beyond the accumulator.
    #[inline]
    pub fn update(&mut self, observation: &[f64]) -> f64 {
        let n = self.dim;
        let r = self.r;
        let state       = &mut self.state[..n];
        let uncertainty = &mut self.uncertainty[..n];
        let mode = self.mode;

        let mut acc = 0.0_f64;

        for k in 0..n {
            // Adaptive Q: process noise scales with current uncertainty
            // to prevent the filter from getting "stuck" in an old state.
            let q_adaptive = match mode {
                FilterMode::Adaptability => self.q * (1.0 + uncertainty[k]),
                FilterMode::Precision => self.q * 0.1, // Less noise for more precision
                FilterMode::Hybrid => self.q * (1.0 + uncertainty[k] * 0.5), // Middle ground
                _ => self.q,
            };
            
            let p = uncertainty[k] + q_adaptive;
            let gain = p / (p + r);
            let innov = observation[k] - state[k];
            
            let innov_sq = innov * innov;
            acc += innov_sq / (p + r);
            
            state[k] += gain * innov;
            uncertainty[k] = p * (1.0 - gain);
        }

        acc / n as f64
    }

    #[allow(dead_code)]
    pub fn get_uncertainty_score(&self) -> f64 {
        self.uncertainty.iter().sum::<f64>() / (self.dim as f64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hybrid_mode_initialization() {
        let kf = CognitiveKalmanFilter::with_mode(10, 0.1, 0.1, FilterMode::Hybrid);
        assert_eq!(kf.dim, 10);
        assert_eq!(kf.mode, FilterMode::Hybrid);
    }
}
