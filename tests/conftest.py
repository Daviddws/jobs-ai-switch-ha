"""Load the custom integration in the test Home Assistant."""

import sys

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load custom_components/jobs_ai."""
    yield


if sys.platform == "win32":
    # Home Assistant's test kit blocks sockets, but on Windows the event loop itself needs a local
    # socket pair. Only for running the tests on a Windows PC; every request is still mocked.
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None
