import pytest


def pytest_addoption(parser):
    parser.addoption("--hardware", action="store_true", help="Run tests against the attached ESP32-C6")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "ble_adapter" in item.fixturenames:
            item.add_marker(pytest.mark.hardware)
        if "hardware" in item.keywords and not config.getoption("--hardware"):
            item.add_marker(pytest.mark.skip(reason="Use --hardware to require the attached ESP32-C6"))
