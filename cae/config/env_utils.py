import os


def _bool(var, default):
    v = os.getenv(var, default=default)
    if v == "True" or v == "true":
        return True
    return False


def _int(var, default):
    return int(os.getenv(var, default=default))


def _float(var, default):
    return float(os.getenv(var, default=default))


def _string(var, default):
    return str(os.getenv(var, default=default))


def _notype(var, default):
    return os.getenv(var, default=default)


def env(var, cast=None, default=None):
    if cast is bool:
        return _bool(var, default)
    elif cast is int:
        return _int(var, default)
    elif cast is float:
        return _float(var, default)
    elif cast is str:
        return _string(var, default)
    else:
        return _notype(var, default)
