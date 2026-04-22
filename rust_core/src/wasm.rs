use wasm_bindgen::prelude::*;
use crate::eml;
use crate::kalman;
use crate::brain;

#[wasm_bindgen]
pub fn wasm_eml_op(x: f64, y: f64) -> f64 {
    eml::eml(x, y)
}

#[wasm_bindgen]
pub fn wasm_exp_eml(x: f64) -> f64 {
    eml::exp_eml(x)
}

#[wasm_bindgen]
pub fn wasm_log_eml(x: f64) -> f64 {
    eml::log_eml(x)
}

#[wasm_bindgen]
pub struct WasmKalmanFilter {
    inner: kalman::CognitiveKalmanFilter,
}

#[wasm_bindgen]
impl WasmKalmanFilter {
    #[wasm_bindgen(constructor)]
    pub fn new(dim: usize, q: f64, r: f64) -> Self {
        Self {
            inner: kalman::CognitiveKalmanFilter::new(dim, q, r),
        }
    }

    pub fn update(&mut self, observation: &[f64]) -> f64 {
        self.inner.update(observation)
    }

    pub fn get_uncertainty_score(&self) -> f64 {
        self.inner.get_uncertainty_score()
    }
}

#[wasm_bindgen]
pub struct WasmPolicyBrain {
    inner: brain::PolicyBrain,
}

#[wasm_bindgen]
impl WasmPolicyBrain {
    #[wasm_bindgen(constructor)]
    pub fn new(input_dim: usize, hidden_dim: usize, output_dim: usize) -> Self {
        Self {
            inner: brain::PolicyBrain::new(input_dim, hidden_dim, output_dim),
        }
    }

    pub fn forward(&mut self, state: &[f64]) -> Vec<f64> {
        self.inner.forward(state)
    }

    pub fn select_action(&mut self, state: &[f64]) -> usize {
        self.inner.select_action(state)
    }

    pub fn train_step(&mut self, state: &[f64], action: usize, reward: f64, lr: f64) {
        self.inner.train_step(state, action, reward, lr);
    }
}
