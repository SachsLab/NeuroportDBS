from pathlib import Path
import importlib.resources as pkg_resources

from qtpy import QtWidgets, QtCore, QtGui


class IniWindow(QtWidgets.QMainWindow):
    """
    A MainWindow that parses multiple QSettings ini files.
    .show() must be manually or by sub-class after adding more widgets
    (presumably using settings).
    """
    def __init__(self):
        super().__init__()
        self._theme_settings = {"colormap": ""}
        self._ipc_settings = {}
        self._settings_paths: [Path] = []

        self._build_ini_paths()
        self.parse_settings()
        self._setup_ipc()

    def __del__(self):
        self._cleanup_ipc()

    def _build_ini_paths(self):
        self._settings_paths: [Path] = []

        # Infer paths to ini files
        root_pkg = __package__.split(".")[0]
        ini_name = type(self).__name__ + '.ini'
        with pkg_resources.path(f"{root_pkg}.resources", "settings") as res_settings_path:
            res_settings_path = res_settings_path
        home_path = Path.home() / f".{root_pkg}"

        # Add paths to settings files in ascending priority
        self._settings_paths.append(res_settings_path / "Style.ini")
        self._settings_paths.append(res_settings_path / "IPC.ini")
        self._settings_paths.append(res_settings_path / ini_name)
        self._settings_paths.append(home_path / "Style.ini")
        self._settings_paths.append(home_path / "IPC.ini")
        self._settings_paths.append(home_path / ini_name)

    def parse_settings(self):
        """
        Parse ini files and populate ._plot_settings.
        Note that some settings (MainWindow) will be applied immediately and won't be stored in _plot_settings.
        Other settings, especially those that are widget-specific, will be stored in _plot_settings.
        Data source settings will be stored in _source_settings for later use by ._init_connection()
        This method should usually be followed by .try_reset_widget()
        """
        for ini_path in self._settings_paths:
            settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

            # Apply MainWindow settings immediately.
            settings.beginGroup("MainWindow")
            keys: list = settings.allKeys()
            if "pos" in keys:
                self.move(settings.value("pos", type=QtCore.QPoint))
            if "size" in keys:
                size_xy: QtCore.QSize = settings.value("size", type=QtCore.QSize)
                self.resize(size_xy)
                self.setMaximumWidth(size_xy.width())
            if "fullScreen" in keys and settings.value("fullScreen", type=bool):
                self.showFullScreen()
            elif "maximized" in keys and settings.value("maximized", type=bool):
                self.showMaximized()
            if "frameless" in keys and settings.value("frameless", type=bool):
                self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            settings.endGroup()

            # theme
            settings.beginGroup("theme")
            # > labels and lines
            for k, t in {
                "labelcolor_active": str, "labelsize_active": int,
                "labelcolor_inactive": str, "labelsize_inactive": int,
                "linewidth": int
            }.items():
                if k in settings.allKeys():
                    self._theme_settings[k] = settings.value(k, type=t)
            # > pencolors
            if "colormap" in settings.allKeys():
                self._theme_settings["colormap"] = settings.value("colormap", defaultValue="custom", type=str)
                self._theme_settings.pop("pencolors", None)
            if self._theme_settings["colormap"] == "custom":
                settings.beginGroup("pencolors")
                chan_ids = [int(_) for _ in settings.childGroups()]
                if "pencolors" not in self._theme_settings:
                    self._theme_settings["pencolors"] = [None] * (max(chan_ids) + 1)
                for c_id in chan_ids:
                    settings.beginGroup(str(c_id))
                    if "name" in settings.allKeys():
                        name = settings.value("name", type=str)
                        self._theme_settings["pencolors"][c_id] = QtGui.QColor(name)
                    else:
                        color_hex = settings.value("value", defaultValue="#ffffff", type=str)
                        self._theme_settings["pencolors"][c_id] = QtGui.QColor(color_hex)
                    settings.endGroup()
                settings.endGroup()
            settings.endGroup()

            # Store / update IPC settings which will be used by subclasses only
            settings.beginGroup("ZeroMQ")
            sock_ids = [int(_) for _ in settings.childGroups()]
            sock_ids.sort()
            for sock_id in sock_ids:
                settings.beginGroup(str(sock_id))
                self._ipc_settings[settings.value("topic", type=str)] = settings.value("port", type=int)
                settings.endGroup()
            settings.endGroup()

    def _setup_ipc(self):
        # Optional method to setup inter-process communication (mostly ZeroMQ pub/sub)
        # e.g.:
        # self._ipc_context = zmq.Context()
        # self._ipc_sock = self._ipc_context.socket(zmq.PUB)
        # self._ipc_sock.bind(f"tcp://*:{self._ipc_settings[topic]}")
        # self._ipc_sock.setsockopt_string(zmq.SUBSCRIBE, topic)
        pass

    def _cleanup_ipc(self):
        # self._ipc_sock.setsockopt(zmq.LINGER, 0)
        # self._ipc_sock.close()
        # self._ipc_context.term()
        pass
