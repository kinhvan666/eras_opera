# tests/conftest.py
import pytest
import os

@pytest.fixture(scope='session', autouse=True)
def set_test_environment_variables():
    """
    Sets up mock environment variables for the test session.
    This runs automatically for all tests.
    """
    test_vars = {
        "OPERA_CLIENT_ID": "test_client_id",
        "OPERA_CLIENT_SECRET": "test_client_secret",
        "OPERA_APP_KEY": "test_app_key",
        "OPERA_BASE_URL": "https://fake-opera-api.com",
        "OPERA_TOKEN_URL": "https://fake-opera-api.com/token",
        "OPERA_HOTEL_ID": "TEST",
        "DATABASE_URL": "postgresql://user:password@fake-db:5432/test_db",
    }

    original_vars = {key: os.environ.get(key) for key in test_vars}

    os.environ.update(test_vars)

    yield

    # Teardown: Restore original environment variables
    for key, value in original_vars.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value

