mod eml;
mod kalman;
mod brain;

use std::time::Instant;
use kalman::CognitiveKalmanFilter;
use brain::PolicyBrain;

fn main() {
    println!("--- 🏗️ XANA STEEL CORE: PERFORMANCE BENCHMARK ---");

    // Sanity: single 384-element dot product baseline
    let w = vec![1.0_f64; 384];
    let x = vec![1.0_f64; 384];
    let n_dot = 100_000;
    let t_dot = std::time::Instant::now();
    for _ in 0..n_dot {
        let s: f64 = w.iter().zip(x.iter()).map(|(&a, &b)| a * b).sum();
        std::hint::black_box(s);
    }
    let dot_ns = t_dot.elapsed().as_nanos() as f64 / n_dot as f64;
    println!("Single dot-384    : {:.1} ns/op ({:.1} GFLOP/s)", dot_ns, 2.0 * 384.0 / dot_ns);
    
    let dim = 384;
    let iterations = 100_000;
    
    // 1. Kalman Filter Benchmark
    println!("Testing Kalman Filter Update x{} (dim={})...", iterations, dim);
    let mut kf = CognitiveKalmanFilter::new(dim, 1e-4, 1e-2);
    let mock_obs = vec![0.5; dim];
    let start_kf = Instant::now();
    for _ in 0..iterations {
        kf.update(&mock_obs);
    }
    let duration_kf = start_kf.elapsed();
    println!("✅ COMPLETED in {:.4}ms (Latency: {:.2}ns)", duration_kf.as_secs_f64() * 1000.0, duration_kf.as_nanos() as f64 / iterations as f64);
    println!("---");
    
    // 2. Policy Brain Benchmark (prevent DCE with std::hint::black_box)
    println!("Testing Policy Brain Forward Pass x{} (dim={}, hidden=64, output=4)...", iterations, dim);
    let mut brain = PolicyBrain::new(dim, 64, 4);
    let start_brain = Instant::now();
    for _ in 0..iterations {
        let probs = brain.forward(&mock_obs);
        std::hint::black_box(probs);
    }
    let duration_brain = start_brain.elapsed();
    println!("✅ COMPLETED in {:.4}ms (Latency: {:.2}ns)", duration_brain.as_secs_f64() * 1000.0, duration_brain.as_nanos() as f64 / iterations as f64);
    println!("---");

    // 3. EML Speed
    println!("Testing EML log_eml reconstruction x1,000,000...");
    let start_eml = Instant::now();
    let mut sum = 0.0;
    for i in 0..1_000_000 {
        sum += eml::log_eml(i as f64 + 1.0);
    }
    let duration_eml = start_eml.elapsed();
    println!("✅ COMPLETED in {:.4}ms (Check sum: {:.2})", duration_eml.as_secs_f64() * 1000.0, sum);
}
