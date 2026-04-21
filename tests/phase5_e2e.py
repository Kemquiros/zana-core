import sys
from pathlib import Path
import numpy as np
import json

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from router.resonance_orchestrator import ResonanceOrchestrator

def test_phase5_e2e():
    print("--- 🌀 XANA PHASE 5: END-TO-END RESONANCE TEST ---")
    
    orchestrator = ResonanceOrchestrator(token_budget=100000)
    
    # 1. Baseline: Contextual Stability (Normal query)
    print("\n[STEP 1] ESTABLE: Consulta de arquitectura estándar")
    q1 = "Explica el flujo de datos entre Neo4j y Redis en la Fase 4."
    emb1 = np.random.randn(384) * 0.01 + 0.1 # Very low variance
    plan1 = orchestrator.route_resonance(q1, emb1)
    print(f"Backend: {plan1['routing']['backend']} | Model: {plan1['routing']['model']}")
    print(f"Innovation Detected: {plan1['resonance']['innovation_detected']}")

    # 2. Innovation: Context Shift (High Surprise)
    print("\n[STEP 2] INNOVACIÓN: Cambio drástico de dominio")
    q2 = "Diseña un plan maestro para la colonización de Marte usando orquestación multi-agente."
    emb2 = np.random.randn(384) * 2.0 + 5.0 # High variance/shift
    plan2 = orchestrator.route_resonance(q2, emb2)
    print(f"Backend: {plan2['routing']['backend']} | Model: {plan2['routing']['model']}")
    print(f"Innovation Detected: {plan2['resonance']['innovation_detected']}")
    
    # 3. Cache Test
    print("\n[STEP 3] CACHE: Verificación de resonancia almacenada")
    # Manually seed cache
    orchestrator.cache.set(q1, "Resultado de arquitectura Fase 4 (Cached)")
    plan3 = orchestrator.route_resonance(q1, emb1)
    print(f"Cache Hit: {plan3.get('cache_hit', False)}")
    
    # 4. Validation
    print("\n--- 🧠 ANALYSIS ---")
    if plan2['resonance']['surprise'] > plan1['resonance']['surprise'] and plan3.get('cache_hit'):
        print("✅ SUCCESS: Phase 5 Resonance components are synchronized.")
    else:
        print("❌ FAIL: Component synchronization error.")

    print(f"Phi Partitioning (Core Reasoning): {plan1['partitions']['core_reasoning']} tokens (61.8%)")

if __name__ == "__main__":
    test_phase5_e2e()
