import typer
from rich.console import Console

console = Console()

def get_hardware_score():
    # Simulación de detección de RAM y VRAM
    ram_gb = 8 # Placeholder
    if ram_gb < 8:
        return "LOW_END"
    return "HIGH_END"

def analyze():
    score = get_hardware_score()
    if score == "LOW_END":
        console.print("[bold red]⚠ Hardware limitado detectado.[/bold red]")
        console.print("Recomendación: Usar modelos de 1B (TinyLlama, Qwen-1.5B).")
        console.print("Opción avanzada: Fine-tuning asistido disponible.")
    else:
        console.print("[bold green]Hardware óptimo.[/bold green]")
        console.print("Recomendación: Llama 3.1 8B.")

