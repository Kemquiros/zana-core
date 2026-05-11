import pytest

from zana.tui.aeon_dna import AeonArchetype, derive_dna


@pytest.mark.asyncio
async def test_high_concurrency_evolution():
    # Simular 100 Aeones evolucionando simultáneamente
    aeons = [derive_dna(f"Aeon_{i}", AeonArchetype.MALKHUT) for i in range(100)]
    for a in aeons:
        a.g25_reputation = 100.0

    # Simular evolución paralela
    results = [a.evolve() for a in aeons]
    assert len(results) == 100
