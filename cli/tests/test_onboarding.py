from pathlib import Path

from cli.tui.onboarding import ensure_env_configured


def test_ensure_env_configured_creates_missing_secrets(tmp_path: Path):
    # Setup: Create a temporary stack_root directory with a mock .env.example
    env_example_content = """# Example .env
ANTHROPIC_API_KEY=your_key_here
POSTGRES_PASSWORD=change_me_strong_password
NEO4J_PASSWORD=zana_neo4j
N8N_PASSWORD=zana_n8n_secure
TELEGRAM_WEBHOOK_SECRET=
N8N_USER=
ZANA_GATEWAY_PORT=54446
"""
    env_example = tmp_path / ".env.example"
    env_example.write_text(env_example_content)

    # Action: Run the ensure_env_configured function
    ensure_env_configured(tmp_path)

    # Assert: Check that .env was created and secrets were generated
    env_file = tmp_path / ".env"
    assert env_file.exists()

    content = env_file.read_text()
    assert "change_me_strong_password" not in content
    assert "zana_neo4j" not in content
    assert "zana_n8n_secure" not in content
    
    # Parse the generated .env
    env_dict = {}
    for line in content.splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_dict[k.strip()] = v.strip()

    assert len(env_dict["POSTGRES_PASSWORD"]) == 32
    assert len(env_dict["NEO4J_PASSWORD"]) == 32
    assert len(env_dict["N8N_PASSWORD"]) == 32
    assert len(env_dict["TELEGRAM_WEBHOOK_SECRET"]) == 32
    assert env_dict["N8N_USER"] == "zana_admin"
    assert env_dict["ANTHROPIC_API_KEY"] == "your_key_here"  # Should not be changed by auto-generator
    assert env_dict["ZANA_GATEWAY_PORT"] == "54446"

def test_ensure_env_configured_preserves_existing_secrets(tmp_path: Path):
    # Setup: Create a .env file with existing valid secrets
    existing_env_content = """# Existing .env
POSTGRES_PASSWORD=my_custom_secure_password123
N8N_USER=my_admin
"""
    env_file = tmp_path / ".env"
    env_file.write_text(existing_env_content)

    # Action
    ensure_env_configured(tmp_path)

    # Assert: Custom secrets should be preserved, missing ones should be added
    content = env_file.read_text()
    env_dict = {}
    for line in content.splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_dict[k.strip()] = v.strip()

    assert env_dict["POSTGRES_PASSWORD"] == "my_custom_secure_password123"
    assert env_dict["N8N_USER"] == "my_admin"
    assert len(env_dict["NEO4J_PASSWORD"]) == 32
