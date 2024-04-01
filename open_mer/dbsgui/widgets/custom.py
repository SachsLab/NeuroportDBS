from qtpy import QtWidgets, QtCore

import open_mer.data_source
from .ini_window import IniWindow
from ..utilities.pyqtgraph import get_colormap


class CustomWidget(QtWidgets.QWidget):
    """
    A simple skeleton widget.
    It is only useful if sub-classed.
    """
    was_closed = QtCore.Signal()

    def __init__(self, source_dict, **kwargs):
        super().__init__()

        # Init member variables
        self.awaiting_close = False
        self.labels = source_dict["channel_names"]
        self.chan_states = source_dict["chan_states"]
        self.samplingRate = source_dict["srate"]

        self._theme = {}
        self._parse_config(**kwargs)

        # Create UI elements
        plot_layout = QtWidgets.QVBoxLayout()
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        self.setLayout(plot_layout)
        self.create_control_panel()
        self.create_plots()
        self.refresh_axes()

    def _parse_config(self, **kwargs):
        self._theme = kwargs["theme"]
        cmap = self._theme["colormap"]
        if cmap != "custom":
            self._theme["pencolors"] = get_colormap(self._theme["colormap"], len(self.chan_states))
        self._theme["color_iterator"] = -1

    def create_control_panel(self):
        cntrl_layout = QtWidgets.QHBoxLayout()
        clear_button = QtWidgets.QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        clear_button.setMaximumWidth(200)
        cntrl_layout.addWidget(clear_button)
        self.layout().addLayout(cntrl_layout)

    def create_plots(self):
        raise TypeError("Must be implemented by sub-class.")

    def refresh_axes(self):
        raise TypeError("Must be implemented by sub-class.")

    def clear(self):
        raise TypeError("Must be implemented by sub-class.")

    def closeEvent(self, evnt):
        super().closeEvent(evnt)
        self.awaiting_close = True
        self.was_closed.emit()


class CustomGUI(IniWindow):
    """
    This application is for monitoring continuous activity from a MER data source.
    """
    widget_cls = CustomWidget

    def __init__(self):
        self._plot_settings = {}
        self._source_settings = {}
        self._data_source = None
        self._plot_widget: CustomWidget | None = None
        # parent IniWindow init will read settings files and setup IPC
        super().__init__()
        self._init_connection()
        # self.try_reset_widget() is auto-triggered from previous line if connection is successful.
        self.show()

    def __del__(self):
        if self._data_source is not None:
            self._data_source.disconnect_requested()
        super().__del__()

    def parse_settings(self):
        super().parse_settings()
        for ini_path in self._settings_paths:
            settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

            # Store / update connection settings which will be triggered after all ini processing
            settings.beginGroup("data-source")
            if "class" in settings.allKeys() and self._data_source is None:
                # Infer data source from ini file
                src_cls = getattr(open_mer.data_source, str(settings.value("class", type=str)))
                self._source_settings["class"] = src_cls
                self._source_settings["settings_path"] = ini_path
            settings.endGroup()

    def _init_connection(self):
        if "class" in self._source_settings and self._source_settings["class"] is not None:
            _data_source = self._source_settings["class"](
                settings_path=self._source_settings["settings_path"],
                on_connect_cb=self.on_source_connected
            )

    @QtCore.Slot(QtCore.QObject)
    def on_source_connected(self, data_source):
        self.data_source = data_source  # Triggers setter --> self.try_reset_widget()

    @property
    def data_source(self):
        return self._data_source

    @data_source.setter
    def data_source(self, value):
        self._data_source = value
        self.try_reset_widget()

    def update(self):
        super().update()
        if self.data_source.is_connected and self._plot_widget:
            self.do_plot_update()

    def do_plot_update(self):
        # abc.abstractmethod not possible because ABC does not work with Qt-derived classes, so raise error instead.
        raise NotImplementedError("This method must be overridden by sub-class.")

    def on_plot_closed(self, force: bool = False):
        if self._plot_widget is not None and (force or self._plot_widget.awaiting_close):
            del self._plot_widget
            self._plot_widget = None

    def try_reset_widget(self):
        self.on_plot_closed(force=True)
        if self.data_source is not None:
            src_dict = self.data_source.data_stats
            self._plot_widget = self.__class__.widget_cls(src_dict,
                                                          theme=self._theme_settings,
                                                          plot=self._plot_settings)
            self._plot_widget.was_closed.connect(self.on_plot_closed)
            self.setCentralWidget(self._plot_widget)
