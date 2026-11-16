"""Noninteractive MySQL configuration; never store or log credentials."""
import os


def mysql_settings(environ=None):
    env = os.environ if environ is None else environ

    def value(*names, default=None):
        return next((env[name] for name in names if env.get(name)), default)

    settings = {
        'host': value('IDX_MYSQL_HOST', 'MYSQL_HOST', 'DB_HOST', default='localhost'),
        'port': value('IDX_MYSQL_PORT', 'MYSQL_PORT', 'DB_PORT', default='3306'),
        'user': value('IDX_MYSQL_USER', 'MYSQL_USER', 'DB_USER'),
        'password': value('IDX_MYSQL_PASSWORD', 'MYSQL_PASSWORD', 'DB_PASSWORD'),
        'database': value('IDX_MYSQL_DATABASE', 'MYSQL_DATABASE', 'DB_NAME'),
        'connection_timeout': 5,
    }
    missing = [name for name in ('user', 'password', 'database') if not settings[name]]
    if missing:
        raise ValueError('Missing MySQL environment configuration: ' + ', '.join(missing))
    try:
        settings['port'] = int(settings['port'])
        if not 1 <= settings['port'] <= 65535:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError('MySQL port must be an integer between 1 and 65535') from None
    return settings
