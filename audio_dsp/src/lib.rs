//! ZANA Audio DSP — feature extraction in Rust.
//! Exposed as a Python extension module via PyO3.
//!
//! Replaces numpy-based extraction with zero-copy Rust:
//!   - WAV PCM parsing (RIFF header, 16-bit LE samples)
//!   - RMS energy
//!   - Zero-crossing rate
//!   - Dominant frequency via radix-2 FFT (Cooley-Tukey)
//!   - Voice activity ratio → WPM estimate

use pyo3::prelude::*;

// ── WAV parsing ───────────────────────────────────────────────────────────────

/// Parses a RIFF WAV file and returns (samples_f32, sample_rate).
/// Supports: PCM 16-bit, mono or stereo, any sample rate.
/// Returns Err string on malformed headers.
fn parse_wav(data: &[u8]) -> Result<(Vec<f32>, u32), String> {
    if data.len() < 44 {
        return Err("WAV too short".into());
    }
    if &data[0..4] != b"RIFF" || &data[8..12] != b"WAVE" {
        return Err("Not a RIFF/WAVE file".into());
    }

    // Walk chunks to find fmt and data
    let mut pos: usize = 12;
    let mut sample_rate: u32 = 0;
    let mut channels: u16 = 1;
    let mut bits_per_sample: u16 = 16;
    let mut pcm_start: usize = 0;
    let mut pcm_len: usize = 0;

    while pos + 8 <= data.len() {
        let chunk_id = &data[pos..pos + 4];
        let chunk_size = u32::from_le_bytes([data[pos+4], data[pos+5], data[pos+6], data[pos+7]]) as usize;
        pos += 8;

        if chunk_id == b"fmt " {
            if chunk_size < 16 { return Err("fmt chunk too small".into()); }
            // audio_format = u16 @ 0 (1 = PCM)
            channels        = u16::from_le_bytes([data[pos+2], data[pos+3]]);
            sample_rate     = u32::from_le_bytes([data[pos+4], data[pos+5], data[pos+6], data[pos+7]]);
            bits_per_sample = u16::from_le_bytes([data[pos+14], data[pos+15]]);
        } else if chunk_id == b"data" {
            pcm_start = pos;
            pcm_len   = chunk_size.min(data.len() - pos);
            break;
        }

        pos += chunk_size + (chunk_size & 1); // word-align
    }

    if sample_rate == 0 || pcm_len == 0 {
        return Err("No audio data found".into());
    }

    let pcm = &data[pcm_start..pcm_start + pcm_len];
    let bytes_per_sample = (bits_per_sample / 8) as usize;
    let frame_size = channels as usize * bytes_per_sample;
    let num_frames = pcm_len / frame_size;

    let mut samples = Vec::with_capacity(num_frames);
    let scale = 1.0 / i16::MAX as f32;

    for i in 0..num_frames {
        let base = i * frame_size;
        // Mix channels to mono, read first channel (16-bit LE assumed)
        let mut sum = 0f32;
        for ch in 0..channels as usize {
            let off = base + ch * bytes_per_sample;
            if off + 1 < pcm.len() {
                let s = i16::from_le_bytes([pcm[off], pcm[off + 1]]);
                sum += s as f32 * scale;
            }
        }
        samples.push(sum / channels as f32);
    }

    Ok((samples, sample_rate))
}

// ── FFT (in-place Cooley-Tukey radix-2, real input) ─────────────────────────

fn next_pow2(n: usize) -> usize {
    let mut p = 1usize;
    while p < n { p <<= 1; }
    p
}

/// Returns magnitude spectrum for real input.
/// Output length = n/2+1.
fn rfft_magnitudes(samples: &[f32]) -> Vec<f32> {
    let n = next_pow2(samples.len());
    let mut re: Vec<f64> = samples.iter().map(|&x| x as f64).collect();
    re.resize(n, 0.0);
    let mut im = vec![0.0f64; n];

    // Bit-reversal permutation
    let mut j = 0usize;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 { j ^= bit; bit >>= 1; }
        j ^= bit;
        if i < j { re.swap(i, j); im.swap(i, j); }
    }

    // Cooley-Tukey iterative
    let mut len = 2usize;
    while len <= n {
        let half = len / 2;
        let ang = -2.0 * std::f64::consts::PI / len as f64;
        let (wr_step, wi_step) = (ang.cos(), ang.sin());
        let mut k = 0;
        while k < n {
            let (mut wr, mut wi) = (1.0f64, 0.0f64);
            for m in 0..half {
                let (ur, ui) = (re[k + m + half] * wr - im[k + m + half] * wi,
                                re[k + m + half] * wi + im[k + m + half] * wr);
                re[k + m + half] = re[k + m] - ur;
                im[k + m + half] = im[k + m] - ui;
                re[k + m] += ur;
                im[k + m] += ui;
                (wr, wi) = (wr * wr_step - wi * wi_step, wr * wi_step + wi * wr_step);
            }
            k += len;
        }
        len <<= 1;
    }

    (0..=n / 2)
        .map(|i| ((re[i] * re[i] + im[i] * im[i]).sqrt()) as f32)
        .collect()
}

// ── Feature extraction ────────────────────────────────────────────────────────

pub struct AudioFeatureResult {
    pub duration_s: f32,
    pub rms_energy: f32,
    pub zero_crossing_rate: f32,
    pub dominant_freq_hz: f32,
    pub speech_rate_wpm: f32,
}

/// Core feature extractor. Operates on WAV bytes.
pub fn extract_features_raw(wav_bytes: &[u8]) -> Result<AudioFeatureResult, String> {
    let (samples, sr) = parse_wav(wav_bytes)?;
    if samples.is_empty() {
        return Err("empty samples".into());
    }

    let n = samples.len();
    let duration_s = n as f32 / sr as f32;

    // RMS energy (clipped to [0,1])
    let rms = (samples.iter().map(|x| x * x).sum::<f32>() / n as f32).sqrt();
    let rms_energy = (rms * 4.0).min(1.0);

    // Zero-crossing rate
    let crossings = samples.windows(2)
        .filter(|w| (w[0] >= 0.0) != (w[1] >= 0.0))
        .count();
    let zcr = crossings as f32 / (n - 1) as f32;

    // Dominant frequency: FFT on first second (or full clip if shorter)
    let window_len = (sr as usize).min(n);
    let mags = rfft_magnitudes(&samples[..window_len]);
    let dom_bin = mags.iter().enumerate()
        .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
        .map(|(i, _)| i)
        .unwrap_or(0);
    let dominant_freq_hz = dom_bin as f32 * sr as f32 / window_len as f32;

    // Voice activity ratio: samples above silence threshold
    let voice_ratio = samples.iter().filter(|&&s| s.abs() > 0.01).count() as f32 / n as f32;
    let speech_rate_wpm = voice_ratio * 180.0;

    Ok(AudioFeatureResult {
        duration_s,
        rms_energy,
        zero_crossing_rate: zcr,
        dominant_freq_hz,
        speech_rate_wpm,
    })
}

// ── PyO3 bindings ─────────────────────────────────────────────────────────────

#[pyclass]
pub struct PyAudioFeatures {
    #[pyo3(get)] pub duration_s: f32,
    #[pyo3(get)] pub rms_energy: f32,
    #[pyo3(get)] pub zero_crossing_rate: f32,
    #[pyo3(get)] pub dominant_freq_hz: f32,
    #[pyo3(get)] pub speech_rate_wpm: f32,
}

#[pymethods]
impl PyAudioFeatures {
    fn __repr__(&self) -> String {
        format!(
            "AudioFeatures(dur={:.2}s rms={:.3} zcr={:.4} freq={:.1}Hz wpm={:.0})",
            self.duration_s, self.rms_energy, self.zero_crossing_rate,
            self.dominant_freq_hz, self.speech_rate_wpm
        )
    }
}

/// Extract acoustic features from WAV bytes.
/// Returns PyAudioFeatures or raises ValueError on parse failure.
#[pyfunction]
pub fn extract_features(wav_bytes: &[u8]) -> PyResult<PyAudioFeatures> {
    match extract_features_raw(wav_bytes) {
        Ok(f) => Ok(PyAudioFeatures {
            duration_s: f.duration_s,
            rms_energy: f.rms_energy,
            zero_crossing_rate: f.zero_crossing_rate,
            dominant_freq_hz: f.dominant_freq_hz,
            speech_rate_wpm: f.speech_rate_wpm,
        }),
        Err(e) => Err(pyo3::exceptions::PyValueError::new_err(e)),
    }
}

/// Infer emotional state from acoustic features.
/// Returns: "agitated" | "excited" | "calm" | "subdued" | "neutral"
#[pyfunction]
pub fn infer_emotion(
    rms_energy: f32,
    zero_crossing_rate: f32,
    speech_rate_wpm: f32,
) -> &'static str {
    if rms_energy > 0.6 && zero_crossing_rate > 0.1 { return "agitated"; }
    if rms_energy > 0.4 && speech_rate_wpm > 160.0  { return "excited";  }
    if rms_energy < 0.1 && speech_rate_wpm < 80.0   { return "calm";     }
    if rms_energy < 0.05                             { return "subdued";  }
    "neutral"
}

#[pymodule]
fn zana_audio_dsp(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_features, m)?)?;
    m.add_function(wrap_pyfunction!(infer_emotion, m)?)?;
    m.add_class::<PyAudioFeatures>()?;
    Ok(())
}
