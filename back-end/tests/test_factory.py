import pytest

from agent.config import Settings
from agent.data import factory
from agent.data.mock import MockSource


def test_build_source_uses_mock_backend(tmp_path):
    settings = Settings(
        agent_model="test",
        data_backend="mock",
        session_db_path=tmp_path / "s.sqlite",
    )
    source = factory.build_source(settings)
    assert isinstance(source, MockSource)


def test_build_source_rejects_postgres_without_connection_info(tmp_path):
    settings = Settings(
        agent_model="test",
        data_backend="postgres",
        database_url=None,
        pghost=None,
        session_db_path=tmp_path / "s.sqlite",
    )
    with pytest.raises(ValueError, match="requires DATABASE_URL"):
        factory.build_source(settings)
