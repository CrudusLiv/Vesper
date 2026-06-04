import pytest
import schedule


@pytest.fixture(autouse=True)
def _clear_schedule():
    """The schedule lib keeps jobs in a module-global; clear before/after each
    test so registrations don't leak across tests."""
    schedule.clear()
    yield
    schedule.clear()
