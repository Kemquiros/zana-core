use zana_idle_zero::*;
use chrono::Local;
use std::fs::File;
use std::io::{BufRead, BufReader};

fn main() {
    println!("  [ R E D   Q U E E N   -   R E A L   W O R L D   ]  ");
    println!("=======================================================");
    
    // 1. Cargar Datos Reales
    let file = File::open("real_data.txt").expect("No se pudo abrir real_data.txt");
    let reader = BufReader::new(file);
    let mut raw_data: Vec<(String, String, f64)> = Vec::new();
    let mut training_values: Vec<f64> = Vec::new();

    for line in reader.lines() {
        if let Ok(l) = line {
            // Buscamos la última tubería para el valor numérico
            if let Some((metadata, val_str)) = l.rsplit_once('|') {
                // Ahora buscamos la primera tubería para el tipo de evento
                if let Some((etype, subject)) = metadata.split_once('|') {
                    let val = val_str.parse::<f64>().unwrap_or(0.0);
                    raw_data.push((etype.to_string(), subject.to_string(), val));
                    training_values.push(val);
                }
            } else {
                println!("⚠️ Línea malformada: {}", l);
            }
        }
    }

    println!("📊 Cargados {} episodios reales para entrenamiento.", training_values.len());

    // 2. Torneo de Evolución contra Realidad
    let mut laboratory = RedQueenIdle::new(30, 32); // 30 Warriors
    println!("🚀 Evolucionando Guerrero contra datos reales (1000 Gen)...");
    
    let mut best_fitness = 0.0;
    for gen in 0..1000 {
        for i in 0..laboratory.active_population.len() {
            let mut warrior = laboratory.active_population[i].clone();
            laboratory.mutate(&mut warrior);
            laboratory.evaluate(&mut warrior, &training_values);
            
            if warrior.fitness >= laboratory.active_population[i].fitness {
                laboratory.active_population[i] = warrior;
            }
            
            if laboratory.active_population[i].fitness > best_fitness {
                best_fitness = laboratory.active_population[i].fitness;
                if gen % 100 == 0 || gen == 0 {
                    println!("[Gen {}] 🏆 Fitness: {:.6}", gen, best_fitness);
                }
            }
        }
    }

    let champion = laboratory.active_population.iter()
        .max_by(|a, b| a.fitness.partial_cmp(&b.fitness).unwrap())
        .unwrap();

    println!("\n👑 GUERRERO CAMPEÓN DE LA REALIDAD: {}", champion.id);
    println!("Fitness: {:.6}", champion.fitness);

    // 3. Ejecución Final (Visualización de la Sorpresa)
    println!("\n{:<10} | {:<40} | {:<10} | {:<10}", "TIPO", "ASUNTO", "VALUE", "SORPRESA");
    println!("{}", "-".repeat(85));

    let mut vm = CognitiveVM::new(32);
    vm.execute(&champion.setup);
    let mut last_output = 0.0;

    for (etype, subject, val) in raw_data {
        vm.memory[0] = val;
        vm.memory[1] = 0.0;
        vm.execute(&champion.predict);
        let output = vm.memory[1];
        let surprise = (output - last_output).abs();
        last_output = output;
        vm.execute(&champion.learn);

        let sub_trunc = if subject.len() > 37 { format!("{}...", &subject[..37]) } else { subject };
        println!("{:<10} | {:<40} | {:<10.6} | {:<10.6}", etype, sub_trunc, val, surprise);
    }

    println!("=======================================================");
    println!("[{}] Evolución y Prueba completada con honor.", Local::now().format("%Y-%m-%d %H:%M:%S"));
}
