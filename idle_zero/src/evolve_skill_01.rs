use zana_idle_zero::*;
use chrono::Local;
use std::fs::File;
use std::io::Read;
use serde_json;

fn main() {
    println!("  [ X A N A   S K I L L   E V O L U T I O N   ]  ");
    println!("  Objetivo: Módulo #01 - Incubadora de Negocios ");
    println!("=======================================================");

    // 1. Cargar ADN Semilla (Génesis del Módulo)
    let mut file = File::open("skill_01_seed.json").expect("No se pudo abrir skill_01_seed.json");
    let mut contents = String::new();
    file.read_to_string(&mut contents).expect("Error al leer semilla");
    let seed: WarriorAlgorithm = serde_json::from_str(&contents).expect("Error al deserializar ADN");

    println!("🧬 ADN Semilla cargado: {} (v1.0.0)", seed.id);

    // 2. Inicializar Laboratorio con la Semilla
    let mut laboratory = RedQueenIdle::new_with_seed(seed, 20, 32);

    // 3. Dataset de Simulación (Vectores de Ideas de Negocio)
    // En el futuro, estos vectores vendrán del Shadow Observer (investigaciones de John)
    let business_data: Vec<f64> = vec![
        0.95, // Idea: SaaS de IA para Fintech (Alta viabilidad)
        0.12, // Idea: Venta de aire embotellado (Baja viabilidad)
        0.88, // Idea: Marketplace de ADN Cognitivo (ZANA)
        0.45, // Idea: Cafetería tradicional (Viabilidad media)
    ];

    println!("🚀 Iniciando Torneo de la Reina Roja (1000 Gen)...");

    let mut best_fitness = 0.0;
    for gen in 0..1000 {
        for i in 0..laboratory.active_population.len() {
            let mut warrior = laboratory.active_population[i].clone();
            laboratory.mutate(&mut warrior);
            
            // Función de Fitness específica para Negocios:
            // Debe premiar la correlación con la viabilidad teórica de business_data.
            laboratory.evaluate(&mut warrior, &business_data);

            if warrior.fitness >= laboratory.active_population[i].fitness {
                laboratory.active_population[i] = warrior;
            }

            if laboratory.active_population[i].fitness > best_fitness {
                best_fitness = laboratory.active_population[i].fitness;
                if gen % 200 == 0 || gen == 0 {
                    println!("[Gen {}] 🏆 Nuevo ADN Champion. Fitness: {:.6}", gen, best_fitness);
                }
            }
        }
    }

    // 4. Presentar al Warrior Especializado
    let champion = laboratory.active_population.iter()
        .max_by(|a, b| a.fitness.partial_cmp(&b.fitness).unwrap())
        .unwrap();

    println!("\n=======================================================");
    println!("👑 WARRIOR ESPECIALIZADO: INCUBADORA DE NEGOCIOS");
    println!("ID: {}", champion.id);
    println!("Fitness en Simulación Financiera: {:.6}", champion.fitness);
    println!("ADN Cristalizado. Listo para migración a Red ZANA Grid.");
    println!("=======================================================");
    
    let now = Local::now().format("%Y-%m-%d %H:%M:%S");
    println!("[{}] Evolución del Módulo #01 completada con honor.", now);
}
