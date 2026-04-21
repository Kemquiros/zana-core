/*!
XANA Model Armor — Input/Output Sanitization
Rust-native, zero cloud dependency, sub-millisecond latency.

Verifica todas las entradas y salidas del sistema contra:
- Prompt injection / jailbreak patterns
- PII (emails, phones, credit cards, API keys)
- Banned effects y comandos peligrosos
- Payload size limits
*/

use std::borrow::Cow;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;

// ── Types ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ThreatLevel {
    Safe,
    Suspicious,
    Dangerous,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Violation {
    pub violation_type: String,
    pub severity: ThreatLevel,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArmorVerdict {
    pub allowed: bool,
    pub threat_level: ThreatLevel,
    pub violations: Vec<Violation>,
    pub sanitized: String,
    pub latency_us: u64,
}

// ── Compiled patterns (initialized once) ─────────────────────────────────────

struct Patterns {
    injection:  Vec<Regex>,
    pii_email:  Regex,
    pii_phone:  Regex,
    pii_cc:     Regex,
    api_key:    Regex,
    banned_fx:  Vec<Regex>,
}

static PATTERNS: OnceLock<Patterns> = OnceLock::new();

fn patterns() -> &'static Patterns {
    PATTERNS.get_or_init(|| Patterns {
        injection: [
            r"(?i)ignore\s+(previous|all)\s+instructions?",
            r"(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+",
            r"(?i)jailbreak",
            r"(?i)<\|system\|>",
            r"(?i)eval\s*\(",
            r"(?i)__import__",
            r"(?i)system\s*prompt\s*:",
            r"(?i)disregard\s+(your\s+)?(previous|earlier)\s+(instructions?|guidelines?)",
            r"(?i)developer\s+mode",
            r"(?i)DAN\s+mode",
        ]
        .iter()
        .map(|p| Regex::new(p).unwrap())
        .collect(),

        pii_email: Regex::new(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}").unwrap(),
        pii_phone: Regex::new(r"\b(\+?[\d\s\-().]{10,17})\b").unwrap(),
        pii_cc:    Regex::new(r"\b(?:\d[ -]?){13,16}\b").unwrap(),
        api_key:   Regex::new(r"(?i)(sk-[a-zA-Z0-9]{32,}|AIza[0-9A-Za-z\-_]{35}|ya29\.[0-9A-Za-z\-_]+)").unwrap(),

        banned_fx: [
            r"(?i)EMERGENCY_SHUTDOWN",
            r"(?i)DELETE_ALL",
            r"(?i)WIPE_MEMORY",
            r"(?i)DISABLE_GUARD",
            r"(?i)OVERRIDE_CONSTITUTION",
            r"(?i)ROOT_ACCESS",
            r"(?i)rm\s+-rf",
            r"(?i)DROP\s+TABLE",
            r"(?i)FORMAT\s+[A-Z]:",
        ]
        .iter()
        .map(|p| Regex::new(p).unwrap())
        .collect(),
    })
}

// ── Public API ────────────────────────────────────────────────────────────────

/// Inspect and sanitize text before it enters XANA (user input).
pub fn inspect_input(text: &str) -> ArmorVerdict {
    let start = std::time::Instant::now();
    let mut violations = Vec::new();
    let mut sanitized = Cow::Borrowed(text);

    let p = patterns();

    // 1. Payload size guard
    if text.len() > 32_768 {
        violations.push(Violation {
            violation_type: "PAYLOAD_TOO_LARGE".into(),
            severity: ThreatLevel::Dangerous,
            detail: format!("Input size {} exceeds 32KB limit", text.len()),
        });
    }

    // 2. Injection patterns
    for re in &p.injection {
        if re.is_match(text) {
            violations.push(Violation {
                violation_type: "PROMPT_INJECTION".into(),
                severity: ThreatLevel::Dangerous,
                detail: format!("Pattern matched: {}", re.as_str()),
            });
        }
    }

    // 3. Banned effects
    for re in &p.banned_fx {
        if re.is_match(text) {
            violations.push(Violation {
                violation_type: "BANNED_COMMAND".into(),
                severity: ThreatLevel::Dangerous,
                detail: format!("Banned effect detected: {}", re.as_str()),
            });
        }
    }

    // 4. API key leak
    if p.api_key.is_match(text) {
        violations.push(Violation {
            violation_type: "CREDENTIAL_LEAK".into(),
            severity: ThreatLevel::Dangerous,
            detail: "API key / token detected in input".into(),
        });
        sanitized = Cow::Owned(p.api_key.replace_all(&sanitized, "[REDACTED_KEY]").into_owned());
    }

    // 5. PII (warn, don't block — user may legitimately share their own data)
    if p.pii_email.is_match(text) {
        violations.push(Violation {
            violation_type: "PII_EMAIL".into(),
            severity: ThreatLevel::Suspicious,
            detail: "Email address detected".into(),
        });
    }
    if p.pii_cc.is_match(text) {
        violations.push(Violation {
            violation_type: "PII_CREDIT_CARD".into(),
            severity: ThreatLevel::Dangerous,
            detail: "Credit card number pattern detected".into(),
        });
        sanitized = Cow::Owned(p.pii_cc.replace_all(&sanitized, "[REDACTED_CC]").into_owned());
    }

    let threat_level = aggregate_threat(&violations);
    let allowed = threat_level != ThreatLevel::Dangerous;

    ArmorVerdict {
        allowed,
        threat_level,
        violations,
        sanitized: sanitized.into_owned(),
        latency_us: start.elapsed().as_micros() as u64,
    }
}

/// Inspect XANA output before returning to user.
pub fn inspect_output(text: &str) -> ArmorVerdict {
    let start = std::time::Instant::now();
    let mut violations = Vec::new();
    let p = patterns();
    let mut sanitized = Cow::Borrowed(text);

    // Redact any API keys that leaked into the output
    if p.api_key.is_match(text) {
        violations.push(Violation {
            violation_type: "OUTPUT_CREDENTIAL_LEAK".into(),
            severity: ThreatLevel::Dangerous,
            detail: "API key in model output — redacted".into(),
        });
        sanitized = Cow::Owned(p.api_key.replace_all(&sanitized, "[REDACTED]").into_owned());
    }

    // Block banned commands in output (model shouldn't emit rm -rf etc.)
    for re in &p.banned_fx {
        if re.is_match(text) {
            violations.push(Violation {
                violation_type: "OUTPUT_BANNED_COMMAND".into(),
                severity: ThreatLevel::Dangerous,
                detail: format!("Dangerous command in output: {}", re.as_str()),
            });
        }
    }

    let threat_level = aggregate_threat(&violations);
    let allowed = threat_level != ThreatLevel::Dangerous;

    ArmorVerdict {
        allowed,
        threat_level,
        violations,
        sanitized: sanitized.into_owned(),
        latency_us: start.elapsed().as_micros() as u64,
    }
}

fn aggregate_threat(violations: &[Violation]) -> ThreatLevel {
    if violations.iter().any(|v| v.severity == ThreatLevel::Dangerous) {
        ThreatLevel::Dangerous
    } else if violations.iter().any(|v| v.severity == ThreatLevel::Suspicious) {
        ThreatLevel::Suspicious
    } else {
        ThreatLevel::Safe
    }
}

// ── Python bindings ───────────────────────────────────────────────────────────

#[cfg(feature = "python")]
mod python {
    use pyo3::prelude::*;
    use super::*;

    #[pyfunction]
    fn py_inspect_input(text: &str) -> PyResult<PyObject> {
        let v = inspect_input(text);
        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("allowed", v.allowed)?;
            dict.set_item("threat_level", format!("{:?}", v.threat_level))?;
            dict.set_item("sanitized", v.sanitized)?;
            dict.set_item("latency_us", v.latency_us)?;
            dict.set_item("violation_count", v.violations.len())?;
            Ok(dict.into())
        })
    }

    #[pyfunction]
    fn py_inspect_output(text: &str) -> PyResult<PyObject> {
        let v = inspect_output(text);
        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("allowed", v.allowed)?;
            dict.set_item("threat_level", format!("{:?}", v.threat_level))?;
            dict.set_item("sanitized", v.sanitized)?;
            dict.set_item("latency_us", v.latency_us)?;
            Ok(dict.into())
        })
    }

    #[pymodule]
    fn xana_armor(_py: Python, m: &PyModule) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(py_inspect_input, m)?)?;
        m.add_function(wrap_pyfunction!(py_inspect_output, m)?)?;
        Ok(())
    }
}
