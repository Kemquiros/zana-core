#![allow(non_local_definitions)]

pub mod eml;
pub mod kalman;
pub mod brain;
pub mod wasm;

// ── Hash-based embedding (no external model, deterministic) ──────────────────

/// Seeded xorshift64 PRNG — uniform [-1, 1].
/// No transcendentals needed: Kalman Surprise only requires a consistent
/// hash-based projection, not a truly Gaussian distribution.
#[inline(always)]
fn xorshift64(mut x: u64) -> impl FnMut() -> f64 {
    move || {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        // Map to [-1, 1] with full 64-bit precision
        (x as i64 as f64) * (1.0 / i64::MAX as f64)
    }
}

/// FNV-1a 64-bit hash of a string.
fn fnv1a(s: &str) -> u64 {
    let mut h: u64 = 14_695_981_039_346_656_037;
    for b in s.bytes() {
        h ^= b as u64;
        h = h.wrapping_mul(1_099_511_628_211);
    }
    h | 1 // ensure non-zero seed
}

/// Produce a `dim`-dimensional embedding from text using seeded xorshift64.
pub fn text_to_embedding(text: &str, dim: usize) -> Vec<f64> {
    let mut rng = xorshift64(fnv1a(text));
    (0..dim).map(|_| rng()).collect()
}

// ── Python bindings ───────────────────────────────────────────────────────────

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::buffer::PyBuffer;

#[cfg(feature = "python")]
#[pyfunction]
fn eml_op(x: f64, y: f64) -> f64 { eml::eml(x, y) }

#[cfg(feature = "python")]
#[pyfunction]
fn exp_eml(x: f64) -> f64 { eml::exp_eml(x) }

#[cfg(feature = "python")]
#[pyfunction]
fn log_eml(x: f64) -> f64 { eml::log_eml(x) }

/// Fast text→embedding function exposed to Python.
#[cfg(feature = "python")]
#[pyfunction]
fn embed_text(text: &str, dim: usize) -> Vec<f64> {
    text_to_embedding(text, dim)
}

#[cfg(feature = "python")]
#[pyclass]
pub struct PyKalmanFilter {
    inner: kalman::CognitiveKalmanFilter,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyKalmanFilter {
    #[new]
    fn new(dim: usize, q: f64, r: f64) -> Self {
        Self { inner: kalman::CognitiveKalmanFilter::new(dim, q, r) }
    }

    /// Standard update from a Python list/array (Vec marshalling).
    fn update(&mut self, observation: Vec<f64>) -> f64 {
        self.inner.update(&observation)
    }

    /// Zero-copy update from a Python buffer (numpy array, memoryview).
    /// Avoids Vec allocation and .tolist() conversion entirely.
    fn update_buffer(&mut self, py: Python, buf: &PyAny) -> PyResult<f64> {
        let buffer: PyBuffer<f64> = PyBuffer::get(buf)?;
        if !buffer.is_c_contiguous() {
            return Err(pyo3::exceptions::PyValueError::new_err("buffer must be C-contiguous"));
        }
        let len = buffer.item_count();
        let ptr = buffer.buf_ptr() as *const f64;
        // SAFETY: buffer is C-contiguous f64, we hold the GIL
        let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
        let _ = py; // GIL held
        Ok(self.inner.update(slice))
    }

    /// Single call: text → embedding → Kalman update.
    /// Zero Python objects cross the boundary — fastest possible path.
    fn update_text(&mut self, text: &str) -> f64 {
        let emb = text_to_embedding(text, self.inner.dim);
        self.inner.update(&emb)
    }

    fn get_uncertainty_score(&self) -> f64 {
        self.inner.get_uncertainty_score()
    }

    fn reset(&mut self) {
        self.inner.state.fill(0.0);
        self.inner.uncertainty.fill(1.0);
    }
}

#[cfg(feature = "python")]
#[pyclass]
struct PyPolicyBrain {
    inner: brain::PolicyBrain,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyPolicyBrain {
    #[new]
    fn new(input_dim: usize, hidden_dim: usize, output_dim: usize) -> Self {
        Self { inner: brain::PolicyBrain::new(input_dim, hidden_dim, output_dim) }
    }

    fn forward(&mut self, state: Vec<f64>) -> Vec<f64> {
        self.inner.forward(&state)
    }

    /// Zero-copy forward pass from a numpy f64 array (buffer protocol).
    fn forward_buffer(&mut self, py: Python, buf: &PyAny) -> PyResult<Vec<f64>> {
        let buffer: PyBuffer<f64> = PyBuffer::get(buf)?;
        if !buffer.is_c_contiguous() {
            return Err(pyo3::exceptions::PyValueError::new_err("buffer must be C-contiguous f64"));
        }
        let ptr = buffer.buf_ptr() as *const f64;
        let len = buffer.item_count();
        let _ = py;
        // SAFETY: C-contiguous f64 buffer, GIL held
        let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
        Ok(self.inner.forward(slice))
    }

    /// Returns argmax action index — avoids Vec→PyList conversion cost.
    fn action_buffer(&mut self, py: Python, buf: &PyAny) -> PyResult<usize> {
        let buffer: PyBuffer<f64> = PyBuffer::get(buf)?;
        if !buffer.is_c_contiguous() {
            return Err(pyo3::exceptions::PyValueError::new_err("buffer must be C-contiguous f64"));
        }
        let ptr = buffer.buf_ptr() as *const f64;
        let len = buffer.item_count();
        let _ = py;
        let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
        let probs = self.inner.forward(slice);
        Ok(probs.iter().enumerate()
            .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
            .map(|(i, _)| i)
            .unwrap_or(0))
    }

    fn select_action(&mut self, state: Vec<f64>) -> usize {
        self.inner.select_action(&state)
    }

    fn train_step(&mut self, state: Vec<f64>, action: usize, reward: f64, lr: f64) {
        self.inner.train_step(&state, action, reward, lr);
    }
}

#[cfg(feature = "python")]
#[pymodule]
fn zana_steel_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(eml_op, m)?)?;
    m.add_function(wrap_pyfunction!(exp_eml, m)?)?;
    m.add_function(wrap_pyfunction!(log_eml, m)?)?;
    m.add_function(wrap_pyfunction!(embed_text, m)?)?;
    m.add_class::<PyKalmanFilter>()?;
    m.add_class::<PyPolicyBrain>()?;
    Ok(())
}
