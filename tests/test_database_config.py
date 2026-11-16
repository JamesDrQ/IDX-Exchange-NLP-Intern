import importlib
from unittest.mock import Mock
import pytest
from scripts.database_config import mysql_settings


def example_env():
    return {'MYSQL_USER': 'fixture_user', 'MYSQL_PASSWORD': 'fixture_only', 'MYSQL_DATABASE': 'fixture_db'}


def test_configuration_requires_explicit_credentials():
    with pytest.raises(ValueError, match='Missing MySQL'):
        mysql_settings({})


def test_aliases_and_precedence():
    env = example_env()
    env['IDX_MYSQL_USER'] = 'preferred_fixture'
    assert mysql_settings(env)['user'] == 'preferred_fixture'
    assert mysql_settings({'DB_USER': 'fixture', 'DB_PASSWORD': 'fixture', 'DB_NAME': 'fixture'})['port'] == 3306


@pytest.mark.parametrize('port', ['0', '65536', 'not-a-port', '-1'])
def test_invalid_port_does_not_disclose_value(port):
    env = example_env(); env['MYSQL_PORT'] = port
    with pytest.raises(ValueError, match='integer between'):
        mysql_settings(env)


def test_loader_import_does_not_connect(monkeypatch):
    import mysql.connector
    connect = Mock(side_effect=AssertionError('Unexpected connection'))
    monkeypatch.setattr(mysql.connector, 'connect', connect)
    import scripts.data_loading as loader
    importlib.reload(loader)
    connect.assert_not_called()


def test_loader_closes_connection_on_failure(monkeypatch, tmp_path):
    from scripts import data_loading as loader
    connection = Mock()
    monkeypatch.setattr(loader, 'mysql_settings', lambda: mysql_settings(example_env()))
    monkeypatch.setattr(loader.mysql.connector, 'connect', Mock(return_value=connection))
    monkeypatch.setattr(loader.pd, 'read_sql', Mock(side_effect=RuntimeError('fixture failure')))
    with pytest.raises(RuntimeError):
        loader.load_sample(tmp_path/'sample.csv')
    connection.close.assert_called_once()


def test_loader_missing_credentials_never_connects(monkeypatch, tmp_path):
    from scripts import data_loading as loader
    monkeypatch.setattr(loader, 'mysql_settings', lambda: mysql_settings({}))
    connect = Mock()
    monkeypatch.setattr(loader.mysql.connector, 'connect', connect)
    with pytest.raises(ValueError):
        loader.load_sample(tmp_path/'sample.csv')
    connect.assert_not_called()
