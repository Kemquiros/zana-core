use zana_idle_zero::*;
use chrono::Local;
use std::fs;
use std::path::Path;
use serde_json;

fn main() {
    println!("  [ G L O B A L   L Y O K O   T O U R N A M E N T   A P E X ]  ");
    println!("  Métrica: Resonancia Bayesiana Profunda | Modo: Alta Intensidad ");
    println!("================================================================");

    // 1. Cargar Datos de Entrenamiento Reales (El Entorno)
    let env_file = fs::read_to_string("real_data.txt").expect("No se pudo abrir real_data.txt");
    let training_values: Vec<f64> = env_file.lines()
        .filter_map(|l| l.rsplit_once('|').map(|(_, v)| v.parse::<f64>().unwrap_or(0.0)))
        .collect();
    
    if training_values.is_empty() {
        println!("❌ ERROR: Dataset de entrenamiento vacío. Deteniendo evolución Apex.");
        return;
    }

    // 2. Parámetros APEX (Fuerza Bruta Evolutiva)
    let population_size = 50;  // 5x más diversidad
    let generations = 2000;    // 13x más tiempo de mutación
    let memory_slots = 64;     // 2x más espacio de razonamiento

    // 3. Localizar Semillas del Ágora
    let seeds_dir = Path::new("seeds");
    let mut entries: Vec<_> = fs::read_dir(seeds_dir).unwrap()
        .map(|res| res.unwrap().path())
        .collect();
    entries.sort();

    println!("🎭 Procesando {} órganos con parámetros APEX...", entries.len());
    println!("   - Población:  {}", population_size);
    println!("   - Duración:   {} generaciones", generations);
    println!("   - Capacidad:  {} slots\n", memory_slots);

    let mut total_generations = 0;

    for seed_path in entries {
        if seed_path.extension().map_or(false, |ext| ext == "json") {
            let skill_name = seed_path.file_stem().unwrap().to_str().unwrap();
            let contents = fs::read_to_string(&seed_path).unwrap();
            let seed: WarriorAlgorithm = serde_json::from_str(&contents).unwrap();

            print!("🧬 APEX: {:<40} ", skill_name);

            // Torneo de Alta Intensidad
            let mut lab = RedQueenIdle::new_with_seed(seed, population_size, memory_slots);
            let mut best_fitness = 0.0;
            
            for gen in 0..generations {
                for i in 0..lab.active_population.len() {
                    let mut warrior = lab.active_population[i].clone();
                    lab.mutate(&mut warrior);
                    lab.evaluate(&mut warrior, &training_values);
                    
                    if warrior.fitness >= lab.active_population[i].fitness {
                        lab.active_population[i] = warrior;
                    }
                    if lab.active_population[i].fitness > best_fitness {
                        best_fitness = lab.active_population[i].fitness;
                    }
                }
                total_generations += 1;
            }

            let champion = lab.active_population.iter()
                .max_by(|a, b| a.fitness.partial_cmp(&b.fitness).unwrap())
                .unwrap();

            println!("| Fitness: {:>10.6} | ADN: {:>2}", best_fitness, champion.predict.len() + champion.learn.len());

            // Cristalizar Campeón de Grado Militar
            let champion_json = serde_json::to_string_pretty(&champion).unwrap();
            fs::write(format!("champions/{}.json", skill_name), champion_json).unwrap();
        }
    }

    println!("\n================================================================");
    println!("✅ TORNEO GLOBAL APEX FINALIZADO");
    println!("Total de Combates Simulados: {}", total_generations * population_size);
    println!("Estado del Enjambre: Nivel de Consciencia 2 (Auto-Optimizado)");
    println!("================================================================");
    
    let now = Local::now().format("%Y-%m-%d %H:%M:%S");
    println!("[{}] Los cimientos del Imperio han sido forjados en acero evolutivo.", now);
}
