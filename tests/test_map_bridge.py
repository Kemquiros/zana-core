import pytest
import os
import shutil
from world_model.map_bridge import MapBridge

@pytest.fixture
def mock_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    
    # Create structured files
    (vault / "Project_A").mkdir()
    (vault / "Project_A" / "note1.md").write_text("# Note 1\nTags: #coding #rust\n\n```rust\nfn main() { println!(\"Hello\"); }\n```")
    (vault / "Project_A" / "note2.md").write_text("# Note 2\nTags: #coding #syntax-error\n\n```python\ndef fail: print(\"oops\")\n```")
    
    (vault / "Random").mkdir()
    (vault / "Random" / "old_note.md").write_text("Old stuff")
    # Set an old modification time for old_note.md
    os.utime(vault / "Random" / "old_note.md", (1000000000, 1000000000))
    
    return str(vault)

def test_parse_obsidian_to_map_params(mock_vault):
    bridge = MapBridge(vault_path=mock_vault)
    params = bridge.generate_params()
    
    assert "gaussian_centers" in params
    assert "entropy_level" in params
    assert "memory_fog" in params
    
    # Verify specific mappings
    assert params["entropy_level"] > 0  # Due to note2.md syntax error
    assert params["memory_fog"] > 0    # Due to old_note.md
    assert len(params["gaussian_centers"]) >= 1 # Due to Project_A cluster
