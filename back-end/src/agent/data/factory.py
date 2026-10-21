"""Composition point: the only module that knows both concrete sources."""

from agent.config import Settings
from agent.data.mock import MockSource
from agent.data.postgres import PostgresSource
from agent.data.simulated_live import SimulatedLiveSource
from agent.domain.ports import WindowSource


def build_source(settings: Settings) -> WindowSource:
    """The window source the settings select: Postgres (checked to be read-only, and
    wrapped to simulate live readings when asked) or the mock. Raises ValueError when
    Postgres is chosen without a database URL or PG* variables.
    """
    if settings.effective_backend == "postgres":
        conninfo = settings.database_conninfo
        if conninfo is None:
            raise ValueError(
                "DATA_BACKEND=postgres requires DATABASE_URL or the PG* variables"
            )
        source = PostgresSource(
            conninfo,
            settings.dashboard_session_id,
            settings.statement_timeout_ms,
            settings.store_batch_size,
        )
        source.check_read_only()
        return SimulatedLiveSource(source) if settings.simulate_live else source
    return MockSource(seed=settings.mock_seed)
