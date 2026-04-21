import sys
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import json

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from episodic.kalman import CognitiveKalmanFilter
from world_model.eml import eml, exp_eml, log_eml

def test_kalman_calibration():
    print("--- 🧪 CALIBRACIÓN DE FILTRO DE KALMAN ---")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    kf = CognitiveKalmanFilter(dim=384)
    
    # 1. Definir secuencias de contexto (Simuladas con frases reales)
    context_sequences = [
        # Contexto A: Arquitectura de Software
        "ZANA es una arquitectura cognitiva diseñada para escalar agentes de IA.",
        "El núcleo de ZANA utiliza Model Context Protocol para interactuar con herramientas.",
        "La fase 4 de la arquitectura implementa un World Model con Neo4j y Redis.",
        
        # Contexto B: Receta de cocina (Cambio drástico)
        "Para preparar empanadas, primero debes hacer la masa con harina y sal.",
        "El relleno puede ser de carne, cebolla y huevo duro.",
        
        # Contexto C: Volver a ZANA (Otro cambio)
        "El filtro de Kalman en ZANA permite gestionar la memoria episódica intra-sesión.",
    ]
    
    print(f"{'Contexto':<60} | {'Surprise':<10} | {'Uncertainty':<10} | {'Status'}")
    print("-" * 100)
    
    surprises = []
    for ctx in context_sequences:
        emb = model.encode(ctx)
        surprise = kf.update(emb)
        uncertainty = kf.get_uncertainty_score()
        surprises.append(surprise)
        
        status = "ESTABLE"
        if surprise > 1.5: # Umbral ajustado para este test
            status = "CAMBIO!"
            
        print(f"{ctx[:57]+'...':<60} | {surprise:10.4f} | {uncertainty:10.4f} | {status}")

    # Análisis
    print("\n--- 🧠 ANÁLISIS DEL FILTRO ---")
    print(f"Surprise máxima: {max(surprises):.4f}")
    print(f"Surprise media: {np.mean(surprises):.4f}")
    
    # El test pasa si la sorpresa al cambiar de contexto (A -> B) es mayor que dentro del mismo contexto (A -> A)
    if surprises[3] > surprises[1]:
        print("✅ CALIBRACIÓN EXITOSA: El filtro detectó el cambio de contexto semántico.")
    else:
        print("❌ FALLO DE CALIBRACIÓN: El filtro no distinguió el cambio de contexto.")

def test_eml_precision():
    print("\n--- 📐 TEST DE PRECISIÓN EML ---")
    x = np.linspace(1, 5, 5)
    
    # Test exp(x)
    expected_exp = np.exp(x)
    actual_exp = exp_eml(x)
    exp_error = np.mean(np.abs(expected_exp - actual_exp))
    
    # Test log(x)
    expected_log = np.log(x)
    actual_log = log_eml(x)
    log_error = np.mean(np.abs(expected_log - actual_log))
    
    print(f"Error medio exp(x) via EML: {exp_error:.2e}")
    print(f"Error medio ln(x) via EML: {log_error:.2e}")
    
    if exp_error < 1e-10 and log_error < 1e-10:
        print("✅ EML PRECISION: Los árboles elementales son matemáticamente exactos.")
    else:
        print("❌ EML ERROR: Desviación numérica significativa.")

if __name__ == "__main__":
    test_kalman_calibration()
    test_eml_precision()
