from importlib.metadata import version


def get_version():
    try:
        return version("pyblade")
    except Exception:
        return "unknown"


__version__ = get_version()
