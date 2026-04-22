import requests
import time


def test_dynamic_rule():
    print("🧪 [TEST] Probando carga dinámica de reglas simbólicas...")

    # 1. Definir una nueva regla "Wisdom"
    new_rule = {
        "name": "Local_ADN_Mining_Boost",
        "conditions": [
            {
                "fact_key": "liquidity",
                "field_path": None,
                "operator": "Gt",
                "value": {"Number": 500000.0},
            },
            {
                "fact_key": "user_reaction_score",
                "field_path": None,
                "operator": "Gt",
                "value": {"Number": 0.8},
            },
        ],
        "actions": [
            {"EmitEffect": "UPGRADE_MINING_RIGS"},
            {
                "LogTrace": "Usuario feliz y con fondos. Invirtiendo en infraestructura de ADN."
            },
        ],
        "explanation_template": "Simbiosis económica detectada. Expandiendo capacidades de minería local.",
    }

    # 2. Enviar regla al Shadow Observer
    resp = requests.post(
        "http://localhost:54444/mcp/reasoning/add_rule", json={"rule": new_rule}
    )
    print(f"Carga de regla: {resp.status_code}")

    # 3. Assert facts to trigger it
    requests.post(
        "http://localhost:54444/mcp/reward",
        json={"user_reaction": 0.9, "comment": "Excellent"},
    )

    # Simular liquidez alta
    # (En una implementación real, esto vendría del módulo de economía,
    # aquí dependemos de lo que el motor tenga en su KB)
    # Por ahora, verificamos si aparece en los rastros si los hechos coinciden.

    time.sleep(1)
    traces = requests.get("http://localhost:54444/mcp/reasoning/traces").json()
    print("Deducciones actuales:")
    for t in traces:
        print(f" - [{t['rule_name']}] {t['deduction']}")


if __name__ == "__main__":
    test_dynamic_rule()
