from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings
from app.db.models import Base


@pytest.mark.parametrize("legacy", [False, True])
def test_api_record_column_migrates_both_fresh_and_existing_databases(tmp_path, monkeypatch, legacy):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    root = Path(__file__).parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    engine = create_engine(url)
    if legacy:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE procurement_cases DROP COLUMN source_record_id"))
        command.stamp(config, "0001")
    command.upgrade(config, "head")
    assert "source_record_id" in {column["name"] for column in inspect(engine).get_columns("procurement_cases")}
