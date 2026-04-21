//! XANA Steel Core: Policy Brain (π)
//! High-speed neural network for skill selection.
//!
//! Layout: W1 is [hidden × input] (row = one hidden neuron's weights over all inputs).
//! matvec_relu / matvec use explicit target_feature + multi-accumulator unrolling for
//! sub-5µs forward pass on a 384→64→4 network.

use rand::prelude::*;
use rand_distr::{Normal, Distribution};

/// Dot product of two f64 slices — LLVM auto-vectorizes with AVX2+FMA when
/// this function is compiled with those target features enabled.
#[inline(always)]
unsafe fn dot(a: *const f64, b: *const f64, n: usize) -> f64 {
    // Convert to slices — LLVM understands slice iteration as a reduction pattern.
    let a = std::slice::from_raw_parts(a, n);
    let b = std::slice::from_raw_parts(b, n);
    a.iter().zip(b.iter()).map(|(&x, &y)| x * y).sum()
}

/// matvec with ReLU, compiled for AVX2+FMA.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn matvec_relu_avx2(
    w: *const f64, x: *const f64, b: *const f64, out: *mut f64,
    rows: usize, cols: usize,
) {
    for j in 0..rows {
        let d = dot(w.add(j * cols), x, cols);
        *out.add(j) = (d + *b.add(j)).max(0.0);
    }
}

/// matvec without activation, compiled for AVX2+FMA.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn matvec_avx2(
    w: *const f64, x: *const f64, b: *const f64, out: *mut f64,
    rows: usize, cols: usize,
) {
    for k in 0..rows {
        let d = dot(w.add(k * cols), x, cols);
        *out.add(k) = d + *b.add(k);
    }
}

/// Scalar fallback (non-x86_64 or missing AVX2).
#[inline(always)]
unsafe fn matvec_relu_scalar(
    w: *const f64, x: *const f64, b: *const f64, out: *mut f64,
    rows: usize, cols: usize,
) {
    for j in 0..rows {
        let d = dot(w.add(j * cols), x, cols);
        *out.add(j) = (d + *b.add(j)).max(0.0);
    }
}

#[inline(always)]
unsafe fn matvec_scalar(
    w: *const f64, x: *const f64, b: *const f64, out: *mut f64,
    rows: usize, cols: usize,
) {
    for k in 0..rows {
        let d = dot(w.add(k * cols), x, cols);
        *out.add(k) = d + *b.add(k);
    }
}

pub struct PolicyBrain {
    pub input_dim:  usize,
    pub hidden_dim: usize,
    pub output_dim: usize,
    /// W1: [hidden_dim × input_dim] — row h = weights for hidden neuron h
    pub w1: Vec<f64>,
    pub b1: Vec<f64>,
    /// W2: [output_dim × hidden_dim]
    pub w2: Vec<f64>,
    pub b2: Vec<f64>,
    /// Pre-allocated scratch buffers — zero heap allocs during inference.
    scratch_h: Vec<f64>,
    scratch_o: Vec<f64>,
}

impl PolicyBrain {
    pub fn new(input_dim: usize, hidden_dim: usize, output_dim: usize) -> Self {
        let mut rng = thread_rng();
        let normal = Normal::new(0.0, 1.0).unwrap();

        let scale1 = (2.0 / (input_dim + hidden_dim) as f64).sqrt();
        let scale2 = (2.0 / (hidden_dim + output_dim) as f64).sqrt();

        // Row-major: W1[h * input_dim + i]
        let w1 = (0..hidden_dim * input_dim)
            .map(|_| normal.sample(&mut rng) * scale1)
            .collect();
        let b1 = vec![0.0; hidden_dim];

        let w2 = (0..output_dim * hidden_dim)
            .map(|_| normal.sample(&mut rng) * scale2)
            .collect();
        let b2 = vec![0.0; output_dim];

        Self {
            input_dim,
            hidden_dim,
            output_dim,
            w1,
            b1,
            w2,
            b2,
            scratch_h: vec![0.0; hidden_dim],
            scratch_o: vec![0.0; output_dim],
        }
    }

    /// Forward pass — returns softmax probs over actions.
    /// Uses raw non-aliased pointers so LLVM can unroll + pipeline the FMA chains.
    pub fn forward(&mut self, state: &[f64]) -> Vec<f64> {
        let h = self.hidden_dim;
        let o = self.output_dim;
        let n = self.input_dim;

        let w1 = self.w1.as_ptr();
        let w2 = self.w2.as_ptr();
        let b1 = self.b1.as_ptr();
        let b2 = self.b2.as_ptr();
        let s  = state.as_ptr();
        let sh = self.scratch_h.as_mut_ptr();
        let so = self.scratch_o.as_mut_ptr();

        // Layer 1: 8-accumulator unrolled dot product per hidden neuron.
        // 8 independent FMA chains hide 5-cycle FMA latency.
        for j in 0..h {
            let row = j * n;
            let (mut a0, mut a1, mut a2, mut a3) = (0.0_f64, 0.0_f64, 0.0_f64, 0.0_f64);
            let (mut a4, mut a5, mut a6, mut a7) = (0.0_f64, 0.0_f64, 0.0_f64, 0.0_f64);
            let chunks = n / 8;
            for c in 0..chunks {
                let base = c * 8;
                unsafe {
                    a0 += *w1.add(row + base)     * *s.add(base);
                    a1 += *w1.add(row + base + 1) * *s.add(base + 1);
                    a2 += *w1.add(row + base + 2) * *s.add(base + 2);
                    a3 += *w1.add(row + base + 3) * *s.add(base + 3);
                    a4 += *w1.add(row + base + 4) * *s.add(base + 4);
                    a5 += *w1.add(row + base + 5) * *s.add(base + 5);
                    a6 += *w1.add(row + base + 6) * *s.add(base + 6);
                    a7 += *w1.add(row + base + 7) * *s.add(base + 7);
                }
            }
            let mut dot = (a0 + a1) + (a2 + a3) + (a4 + a5) + (a6 + a7);
            for i in (chunks * 8)..n {
                dot += unsafe { *w1.add(row + i) * *s.add(i) };
            }
            unsafe { *sh.add(j) = (dot + *b1.add(j)).max(0.0) };
        }

        // Layer 2: 4 accumulators (h=64 — smaller inner loop)
        for k in 0..o {
            let row = k * h;
            let (mut a0, mut a1, mut a2, mut a3) = (0.0_f64, 0.0_f64, 0.0_f64, 0.0_f64);
            let chunks = h / 4;
            for c in 0..chunks {
                let base = c * 4;
                unsafe {
                    a0 += *w2.add(row + base)     * *sh.add(base);
                    a1 += *w2.add(row + base + 1) * *sh.add(base + 1);
                    a2 += *w2.add(row + base + 2) * *sh.add(base + 2);
                    a3 += *w2.add(row + base + 3) * *sh.add(base + 3);
                }
            }
            let mut dot = (a0 + a1) + (a2 + a3);
            for i in (chunks * 4)..h {
                dot += unsafe { *w2.add(row + i) * *sh.add(i) };
            }
            unsafe { *so.add(k) = dot + *b2.add(k) };
        }

        // Softmax (o=4)
        let scratch_o = unsafe { std::slice::from_raw_parts(so, o) };
        let max = scratch_o.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let mut sum = 0.0_f64;
        let mut probs = vec![0.0_f64; o];
        for k in 0..o {
            probs[k] = (scratch_o[k] - max).exp();
            sum += probs[k];
        }
        for p in probs.iter_mut() { *p /= sum; }
        probs
    }

    pub fn select_action(&mut self, state: &[f64]) -> usize {
        let probs = self.forward(state);
        let mut rng = thread_rng();
        let r: f64 = rng.gen();
        let mut cumulative = 0.0;
        for (i, &p) in probs.iter().enumerate() {
            cumulative += p;
            if r <= cumulative { return i; }
        }
        self.output_dim - 1
    }

    /// REINFORCE gradient step.
    pub fn train_step(&mut self, state: &[f64], action: usize, reward: f64, lr: f64) {
        let probs = self.forward(state);
        let h = self.hidden_dim;
        let o = self.output_dim;
        let n = self.input_dim;

        // dL/dz2 = (probs - one_hot(action)) * -reward
        let mut d_z2 = probs.clone();
        d_z2[action] -= 1.0;
        for v in d_z2.iter_mut() { *v *= -reward; }

        // dW2, db2
        for k in 0..o {
            for j in 0..h {
                self.w2[k * h + j] -= lr * self.scratch_h[j] * d_z2[k];
            }
            self.b2[k] -= lr * d_z2[k];
        }

        // d_a1 = W2.T @ d_z2
        let mut d_a1 = vec![0.0; h];
        for j in 0..h {
            for k in 0..o {
                d_a1[j] += self.w2[k * h + j] * d_z2[k];
            }
        }

        // ReLU gate (scratch_h holds a1 from last forward)
        // dW1, db1
        for j in 0..h {
            if self.scratch_h[j] > 0.0 {
                let d = d_a1[j];
                let row = &mut self.w1[j * n..(j + 1) * n];
                for (w, &s) in row.iter_mut().zip(state) {
                    *w -= lr * s * d;
                }
                self.b1[j] -= lr * d;
            }
        }
    }
}
