use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorData {
    pub machine_id: String,
    pub sensor_type: String, // "VIBRATION", "TEMPERATURE", "LOAD"
    pub value: f64,
    pub unit: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MachineHealth {
    pub machine_id: String,
    pub overall_status: f64, // 0.0 to 1.0 (1.0 is healthy)
    pub failure_probability: f64,
    pub last_update: DateTime<Utc>,
    pub surprise_level: f64, // Bayesian Surprise
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActuatorCommand {
    pub machine_id: String,
    pub command: String, // "SHUTDOWN", "REDUCE_LOAD", "COOL_DOWN", "CALIBRATE"
    pub target_value: f64,
    pub priority: u8, // 1 to 10
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndustrialIntervention {
    pub id: String,
    pub machine_id: String,
    pub trigger_reason: String,
    pub command: ActuatorCommand,
    pub timestamp: DateTime<Utc>,
    pub status: String, // "PENDING", "EXECUTED", "REJECTED"
}

pub struct IndustrialCore {
    pub machines: HashMap<String, MachineHealth>,
    pub active_interventions: Vec<IndustrialIntervention>,
}

impl IndustrialCore {
    pub fn new() -> Self {
        Self {
            machines: HashMap::new(),
            active_interventions: vec![],
        }
    }

    pub fn process_sensor(&mut self, data: SensorData) -> MachineHealth {
        let entry = self.machines.entry(data.machine_id.clone()).or_insert(MachineHealth {
            machine_id: data.machine_id.clone(),
            overall_status: 1.0,
            failure_probability: 0.0,
            last_update: Utc::now(),
            surprise_level: 0.0,
        });

        // Refined Kalman-lite surprise detection
        // State = expected value, Uncertainty = deviation
        let q = 0.01; // Process noise
        let r = 0.1;  // Measurement noise
        
        let p = entry.failure_probability + q;
        let gain = p / (p + r);
        
        // Innovation based on deviation from "normal" (0.0 failure prob)
        // Normalized by sensor type
        let normalized_val = match data.sensor_type.as_str() {
            "TEMPERATURE" => (data.value - 40.0) / 100.0,
            "VIBRATION" => data.value / 10.0,
            "LOAD" => data.value / 100.0,
            _ => 0.0
        }.max(0.0);

        let innov = (normalized_val - entry.failure_probability).abs();
        let surprise = (innov * innov) / (p + r);
        
        entry.surprise_level = surprise.min(1.0);
        entry.failure_probability += gain * (normalized_val - entry.failure_probability);
        entry.overall_status = (1.0 - entry.failure_probability).max(0.0);
        entry.last_update = Utc::now();

        entry.clone()
    }

    pub fn evaluate_interventions(&mut self, machine_id: &str) -> Option<IndustrialIntervention> {
        let health = self.machines.get(machine_id)?;
        if health.overall_status < 0.4 {
            let command = ActuatorCommand {
                machine_id: machine_id.to_string(),
                command: "EMERGENCY_SHUTDOWN".to_string(),
                target_value: 0.0,
                priority: 10,
            };
            let intervention = IndustrialIntervention {
                id: uuid::Uuid::new_v4().to_string(),
                machine_id: machine_id.to_string(),
                trigger_reason: format!("Critical status: {:.2}%", health.overall_status * 100.0),
                command,
                timestamp: Utc::now(),
                status: "PENDING".to_string(),
            };
            self.active_interventions.push(intervention.clone());
            return Some(intervention);
        }
        None
    }

    pub fn update_intervention(&mut self, id: &str, status: &str) -> bool {
        if let Some(intervention) = self.active_interventions.iter_mut().find(|i| i.id == id) {
            intervention.status = status.to_string();
            return true;
        }
        false
    }
}
