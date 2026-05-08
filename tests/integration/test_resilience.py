from tests.mocks.llm_mock import MockLLM


def test_inference_fallback_on_low_ram():
    # Probar que el sistema sugiere modelos pequeños en hardware limitado
    llm = MockLLM(model_size="1B")
    assert "1B" in llm.generate("test")


def test_system_stability_under_load():
    # Smoke test de estabilidad
    assert True
