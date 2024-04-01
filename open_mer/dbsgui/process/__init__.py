import importlib.resources as pkg_resources
from pathlib import Path

from qtpy import QtCore

from .trajectory import SnippetWorker


__all__ = ["build_ini_paths", "parse_ini", "SnippetWorker"]


def build_ini_paths() -> list[Path]:
    # Infer paths to ini files
    res_settings_path = pkg_resources.files("open_mer.resources") / "settings"
    home_path = Path.home() / ".open_mer"

    return [
        res_settings_path / "IPC.ini",
        res_settings_path / "FeaturesGUI.ini",  # for buffer settings
        home_path / "IPC.ini",
        home_path / "FeaturesGUI.ini"  # for buffer settings
    ]


def parse_ini(ini_paths) -> (dict, dict, dict):
    ipc_settings = {}
    buffer_settings = {}
    feature_settings = {}
    for ini_path in ini_paths:
        settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

        # Store / update IPC settings which will be used by subclasses only
        settings.beginGroup("ZeroMQ")
        sock_ids = [int(_) for _ in settings.childGroups()]
        sock_ids.sort()
        for sock_id in sock_ids:
            settings.beginGroup(str(sock_id))
            ipc_settings[settings.value("topic", type=str)] = settings.value("port", type=int)
            settings.endGroup()
        settings.endGroup()

        # Buffer
        settings.beginGroup("buffer")
        for k, t in {
            "highpass": bool,
            "buffer_duration": float,
            "sample_duration": float,
            "delay_duration": float,
            "validity_threshold": float,
            "overwrite_depth": bool,
            # electrode_settings ?!
            # chk_threshold ?!
        }.items():
            if k in settings.allKeys():
                buffer_settings[k] = settings.value(k, type=t)
        settings.endGroup()  # buffer

        settings.beginGroup("data-source")
        for k, t in {"sampling_group": int}.items():
            if k in settings.allKeys():
                buffer_settings[k] = settings.value(k, type=t)
        settings.endGroup()

        # Features (used by Features_Process)
        settings.beginGroup("features")
        feat_inds = [int(_) for _ in settings.childGroups()]
        feat_inds.sort()
        for f_ind in feat_inds:
            settings.beginGroup(str(f_ind))
            feature_settings[f_ind] = (settings.value("name", type=str), settings.value("enable", type=bool))
            settings.endGroup()
        settings.endGroup()  # features
    return ipc_settings, buffer_settings, feature_settings
