from importlib.metadata import PackageNotFoundError, version


def get_version(package_name: str = "pyblade"):
    try:
        return version(package_name)
    except PackageNotFoundError:
        print("'{package_name}' is not installed via pip")
        return
