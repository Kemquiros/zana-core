use rand::prelude::*;
use serde::{Deserialize, Serialize};
use rayon::prelude::*;

// ==========================================
// 1. EL LENGUAJE DEL ADN ADVERSARIO (DRQ-EML)
// ==========================================

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum Op {
    NoOp,
    Add, Subtract, Multiply, Divide,
    Exp, Log, Sin, Cos,
    GaussianSample,
    EmulativeCall,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Instruction {
    pub op: Op,
    pub out_addr: usize,
    pub in1_addr: usize,
    pub in2_addr: usize,
    pub constant: f64,
    pub model_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WarriorAlgorithm {
    pub id: String,
    pub generation: u32,
    pub setup: Vec<Instruction>,
    pub predict: Vec<Instruction>,
    pub learn: Vec<Instruction>,
    pub fitness: f64,
}

// ==========================================
// 2. MÁQUINA VIRTUAL (COGNITIVE VM)
// ==========================================

pub struct CognitiveVM {
    pub memory: Vec<f64>,
}

impl CognitiveVM {
    pub fn new(size: usize) -> Self {
        Self { memory: vec![0.0; size] }
    }

    pub fn execute(&mut self, instructions: &[Instruction]) {
        for instr in instructions {
            let val1 = *self.memory.get(instr.in1_addr).unwrap_or(&0.0);
            let val2 = *self.memory.get(instr.in2_addr).unwrap_or(&0.0);
            
            let result = match instr.op {
                Op::NoOp => val1,
                Op::Add => val1 + val2,
                Op::Subtract => val1 - val2,
                Op::Multiply => val1 * val2,
                Op::Divide => if val2 != 0.0 { val1 / val2 } else { 0.0 },
                Op::Exp => val1.exp(),
                Op::Log => if val1 > 0.0 { val1.ln() } else { 0.0 },
                Op::Sin => val1.sin(),
                Op::Cos => val1.cos(),
                Op::GaussianSample => {
                    let mut rng = thread_rng();
                    rng.gen_range(instr.constant..instr.constant + 1.0) // Simplificado
                },
                Op::EmulativeCall => val1, // Mock call
            };

            if let Some(m) = self.memory.get_mut(instr.out_addr) {
                *m = result;
            }
        }
    }
}

// ==========================================
// 3. EL MOTOR RED QUEEN (TORNEO PARALELO)
// ==========================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PoEBlock {
    pub warrior: WarriorAlgorithm,
    pub skill_id: String,
    pub timestamp: i64,
    pub miner_id: String,
    pub verification_hash: String,
}

pub struct RedQueenIdle {
    pub active_population: Vec<WarriorAlgorithm>,
    pub memory_size: usize,
}

impl RedQueenIdle {
    pub fn new(pop_size: usize, memory_size: usize) -> Self {
        let active_population = (0..pop_size).map(|_| WarriorAlgorithm {
            id: uuid::Uuid::new_v4().to_string(),
            generation: 0,
            setup: vec![],
            predict: vec![],
            learn: vec![],
            fitness: 0.0,
        }).collect();

        Self { active_population, memory_size }
    }

    pub fn new_with_seed(seed: WarriorAlgorithm, pop_size: usize, memory_size: usize) -> Self {
        let active_population = (0..pop_size).map(|_| {
            let mut warrior = seed.clone();
            warrior.id = uuid::Uuid::new_v4().to_string();
            warrior
        }).collect();

        Self { active_population, memory_size }
    }

    pub fn mutate(&self, algo: &mut WarriorAlgorithm) {
        let mut rng = thread_rng();
        let target_vec = match rng.gen_range(0..3) {
            0 => &mut algo.setup,
            1 => &mut algo.predict,
            _ => &mut algo.learn,
        };

        let mutation_type = rng.gen_range(0..3);
        match mutation_type {
            0 => { // Add
                target_vec.push(Instruction {
                    op: match rng.gen_range(1..10) {
                        1 => Op::Add, 2 => Op::Subtract, 3 => Op::Multiply,
                        4 => Op::Divide, 5 => Op::Exp, 6 => Op::Log,
                        7 => Op::Sin, 8 => Op::Cos, _ => Op::GaussianSample,
                    },
                    out_addr: rng.gen_range(0..self.memory_size),
                    in1_addr: rng.gen_range(0..self.memory_size),
                    in2_addr: rng.gen_range(0..self.memory_size),
                    constant: rng.gen_range(-1.0..1.0),
                    model_id: None,
                });
            }
            1 => { if !target_vec.is_empty() { target_vec.remove(rng.gen_range(0..target_vec.len())); } }
            _ => { // Modify
                if !target_vec.is_empty() {
                    let idx = rng.gen_range(0..target_vec.len());
                    target_vec[idx].constant += rng.gen_range(-0.1..0.1);
                }
            }
        }
        algo.generation += 1;
    }

    pub fn evaluate(&self, algo: &mut WarriorAlgorithm, data: &Vec<f64>) {
        let mut vm = CognitiveVM::new(self.memory_size);
        vm.execute(&algo.setup);
        let mut last_prediction = 0.0;
        let mut total_diff = 0.0;
        let mut is_stable = true;

        for obs in data {
            vm.memory[0] = *obs;
            vm.memory[1] = 0.0;
            vm.execute(&algo.predict);
            let prediction = vm.memory[1];
            if !prediction.is_finite() { is_stable = false; break; }
            total_diff += (prediction - last_prediction).abs();
            last_prediction = prediction;
            vm.execute(&algo.learn);
        }

        if !is_stable { algo.fitness = 0.0; return; }
        let complexity = (algo.setup.len() + algo.predict.len() + algo.learn.len()) as f64;
        let complexity_penalty = complexity * 0.005;
        algo.fitness = (total_diff / data.len() as f64) - complexity_penalty;
        if algo.fitness < 0.0 { algo.fitness = 0.0; }
    }

    /// MINERÍA PARALELA (Hito PoE)
    pub fn mine_parallel(&mut self, data: &Vec<f64>, iterations: usize) {
        println!("⛏️ [IDLE-ZERO] Minería Cognitiva Paralela ({} hilos)...", rayon::current_num_threads());
        let memory_size = self.memory_size;

        for _ in 0..iterations {
            self.active_population.par_iter_mut().for_each(|warrior| {
                let lab_helper = RedQueenIdle { active_population: vec![], memory_size };
                let mut child = warrior.clone();
                lab_helper.mutate(&mut child);
                lab_helper.evaluate(&mut child, data);
                if child.fitness >= warrior.fitness { *warrior = child; }
            });
        }
    }
}

// ==========================================
// 4. LA REINA DEL ENJAMBRE (META-EVOLUTIONARY MODULE)
// ==========================================

pub struct HiveQueen {
    pub client: reqwest::Client,
    pub known_peers: Vec<String>,
}

impl HiveQueen {
    pub fn new() -> Self {
        Self { client: reqwest::Client::new(), known_peers: vec![] }
    }

    /// Descubre nodos activos en el enjambre a través del Registro Central
    pub async fn discover_peers(&mut self, registry_addr: &str) {
        println!("🔍 [Hive Queen] Consultando Registro Central para descubrir pares...");
        match self.client.get(&format!("{}/nodes", registry_addr)).send().await {
            Ok(res) if res.status().is_success() => {
                if let Ok(nodes) = res.json::<Vec<serde_json::Value>>().await {
                    self.known_peers = nodes.iter()
                        .filter_map(|n| n.get("addr").and_then(|a| a.as_str()).map(|s| s.to_string()))
                        .collect();
                    println!("✅ [Discovery] Encontrados {} nodos en la Red ZANA Grid.", self.known_peers.len());
                }
            }
            _ => { println!("⚠️ [Discovery] No se pudo contactar con el Registro Central."); }
        }
    }

    pub async fn scout_for_dna(&self) -> Vec<WarriorAlgorithm> {
        println!("🐝 [Hive Queen] Scanning peer network...");
        let mut discovered_dna = vec![];
        for peer in &self.known_peers {
            match self.client.post(&format!("{}/api/export", peer)).send().await {
                Ok(res) if res.status().is_success() => {
                    if let Ok(dna) = res.json::<WarriorAlgorithm>().await { discovered_dna.push(dna); }
                }
                _ => {}
            }
        }
        discovered_dna
    }

    pub fn integrate_dna(&self, lab: &mut RedQueenIdle, foreign_dna: Vec<WarriorAlgorithm>) {
        for dna in foreign_dna {
            if let Some(weakest) = lab.active_population.iter_mut().min_by(|a, b| a.fitness.partial_cmp(&b.fitness).unwrap()) {
                if dna.fitness > weakest.fitness { *weakest = dna; }
            }
        }
    }
}
