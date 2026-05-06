import pytest
from cli.commands.world import forge
from cli.tui.aeon_dna import derive_dna, AeonArchetype

def test_full_archon_lifecycle():
    # 1. Init Aeon
    aeon = derive_dna("Babylon", AeonArchetype.MALKHUT)
    assert aeon.g25_reputation == 0.0
    
    # 2. Forge Relic
    # 3. Duel (Reputation growth)
    aeon.g25_reputation += 100.0
    
    # 4. Evolution to T2 (GEVURAH)
    new_aeon = aeon.evolve()
    assert new_aeon.archetype == AeonArchetype.GEVURAH
