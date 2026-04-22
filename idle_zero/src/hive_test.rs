use zana_idle_zero::*;
use tokio;

#[tokio::main]
async fn main() {
    println!("  [ H I V E   Q U E E N   -   L Y O K O   S C O U T ]  ");
    println!("=======================================================");

    // 1. Inicializar el Laboratorio Local y la Reina
    let mut laboratory = RedQueenIdle::new(5, 16);
    let mut queen = HiveQueen::new();

    println!("🚀 La Reina inicia el vuelo...");

    // 2. Descubrir pares a través del Registro
    queen.discover_peers("http://localhost:50000").await;

    // 3. Simular el ciclo de la Reina
    let foreign_dna = queen.scout_for_dna().await;

    
    if foreign_dna.is_empty() {
        println!("⚠️ No se encontró ADN superior en la Red ZANA Grid (¿El servidor MCP está arriba?)");
    } else {
        println!("🧬 Procesando {} muestras de ADN recolectadas...", foreign_dna.len());
        queen.integrate_dna(&mut laboratory, foreign_dna);
    }

    println!("=======================================================");
    println!("Exploración finalizada. El enjambre ha evolucionado.");
}
