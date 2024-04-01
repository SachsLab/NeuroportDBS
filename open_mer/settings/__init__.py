def parse_ini_try_numeric(settings, key):
    putative = settings.value(key)
    if putative == 'false':
        return False
    elif putative == 'true':
        return True
    try:
        res = settings.value(key, type=int)
    except TypeError:
        res = None
    if res is None or (res == 0 and putative):
        try:
            res = settings.value(key, type=float)
        except TypeError:
            res = None
    if res is None or (res == 0.0 and putative):
        res = settings.value(key)
    return res


def locate_ini(ini_name):
    from pathlib import Path
    from qtpy import QtCore
    ini_path = Path(ini_name)
    if ini_path.exists():
        _settings_path = ini_path
    else:
        # Try home / .open_mer first
        home_dir = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.HomeLocation))
        ini_path = home_dir / '.open_mer' / ini_path.name
        if ini_path.exists():
            _settings_path = ini_path
        else:
            # Use default ini that ships with module.
            _settings_path = Path(__file__).parents[1] / "resources" / "settings" / ini_path.name
    return _settings_path

