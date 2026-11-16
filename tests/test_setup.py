import sys
import mysql.connector
import pandas as pd
import nltk


def test_python_version():
    assert sys.version_info >= (3, 11)


def test_packages():
    assert pd is not None
    assert nltk is not None


def test_mysql_connection():
    import os
    import pytest
    from scripts.database_config import mysql_settings

    if os.getenv("RUN_MYSQL_INTEGRATION") != "1":
        pytest.skip("Live MySQL check requires RUN_MYSQL_INTEGRATION=1")
    settings = mysql_settings()
    conn = mysql.connector.connect(**settings)
    try:
        assert conn.is_connected()
    finally:
        conn.close()
