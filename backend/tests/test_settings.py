from __future__ import annotations

from app.config.settings import BACKEND_ROOT, Settings


def test_reads_env_file_and_resolves_relative_paths(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "DATABASE_PATH=./data/notes.db\n"
        'CORS_ORIGINS=["http://localhost:4000"]\n'
        "MAX_UPLOAD_MB=2\n"
        "BACKEND_PORT=9000\n"
    )
    settings = Settings(_env_file=env)

    assert settings.database_path == BACKEND_ROOT / "data/notes.db"
    assert settings.cors_origins == ["http://localhost:4000"]
    assert settings.max_upload_bytes == 2 * 1024 * 1024


def test_absolute_paths_are_kept(tmp_path):
    env = tmp_path / ".env"
    env.write_text(f"CONFIG_DIR={tmp_path}\n")
    assert Settings(_env_file=env).config_dir == tmp_path
