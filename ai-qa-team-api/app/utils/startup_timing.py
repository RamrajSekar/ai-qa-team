"""Fixed-label startup timings, with no exception messages or connection details."""
from contextlib import contextmanager
from time import perf_counter

from app.utils.logger import logger


@contextmanager
def startup_timing(stage):
    if stage not in {"mongo_indexes", "mongo_probe", "redis_probe"}:
        raise ValueError("Unknown startup stage")
    started = perf_counter()
    outcome = "completed"
    try:
        yield
    except BaseException:
        outcome = "failed"
        raise
    finally:
        logger.info("api_startup stage=%s duration_ms=%d outcome=%s",
                    stage, round((perf_counter() - started) * 1000), outcome)
