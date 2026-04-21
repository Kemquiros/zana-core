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

        let mut surprise = 0.0;
        match data.sensor_type.as_str() {
            "TEMPERATURE" => { if data.value > 85.0 { surprise = (data.value - 85.0) / 100.0; } },
            "VIBRATION" => { if data.value > 5.0 { surprise = (data.value - 5.0) / 10.0; } },
            "LOAD" => { if data.value > 95.0 { surprise = (data.value - 95.0) / 100.0; } },
            _ => {}
        }

        entry.surprise_level = surprise.min(1.0);
        entry.failure_probability = (entry.failure_probability * 0.8 + surprise * 0.2).min(1.0);
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
