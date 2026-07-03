from pathlib import Path

from app.core.config import get_settings


def test_settings_uses_backend_env_path():
    settings = get_settings()

    assert Path(settings.env_file_path).name == ".env"
    assert Path(settings.env_file_path).parent.name == "backend"
