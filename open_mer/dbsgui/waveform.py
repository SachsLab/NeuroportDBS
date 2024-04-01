import numpy as np
from qtpy import QtCore, QtWidgets
import pyqtgraph as pg

from .utilities.pyqtgraph import parse_color_str
from .widgets.custom import CustomGUI, CustomWidget


class WaveformWidget(CustomWidget):

    def __init__(self, *args, theme={}, plot={}):
        self.DTT = None
        self.plot_config = {}
        super().__init__(*args, theme=theme, plot=plot)

    def _parse_config(self, theme={}, plot={}):
        super()._parse_config(theme=theme)
        plot = plot["plot"]
        self.plot_config["x_range"] = (plot["x_start"], plot["x_stop"])
        self.plot_config["y_range"] = plot["y_range"]
        self.plot_config["n_waveforms"] = plot["n_waveforms"]
        self.plot_config["unit_scaling"] = plot["unit_scaling"]

    def create_control_panel(self):
        # Create control panel
        cntrl_layout = QtWidgets.QHBoxLayout()
        # +/- amplitude range
        cntrl_layout.addWidget(QtWidgets.QLabel("+/- "))
        range_edit = QtWidgets.QLineEdit("{:.2f}".format(250))  # Value overridden in create_plots
        range_edit.setObjectName("range_LineEdit")
        range_edit.setMinimumHeight(23)
        range_edit.setMaximumWidth(80)
        range_edit.editingFinished.connect(self.on_range_edit_editingFinished)
        cntrl_layout.addWidget(range_edit)
        cntrl_layout.addStretch()

        # N Spikes
        cntrl_layout.addWidget(QtWidgets.QLabel("N Spikes "))
        n_spikes_edit = QtWidgets.QLineEdit("{}".format(100))  # Value overridden in create_plots
        n_spikes_edit.setObjectName("n_spikes_LineEdit")
        n_spikes_edit.setMaximumWidth(80)
        n_spikes_edit.setMinimumHeight(23)
        n_spikes_edit.editingFinished.connect(self.on_n_spikes_edit_editingFinished)
        cntrl_layout.addWidget(n_spikes_edit)
        cntrl_layout.addStretch()

        # Clear button
        clear_button = QtWidgets.QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        clear_button.setMaximumWidth(80)
        cntrl_layout.addWidget(clear_button)
        # Finish
        self.layout().addLayout(cntrl_layout)

    def create_plots(self):
        # Update widget values without triggering signals
        range_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, name="range_LineEdit")
        prev_state = range_edit.blockSignals(True)
        range_edit.setText(str(self.plot_config['y_range']))
        range_edit.blockSignals(prev_state)

        n_spikes_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, name="n_spikes_LineEdit")
        prev_state = n_spikes_edit.blockSignals(True)
        n_spikes_edit.setText(str(self.plot_config['n_waveforms']))
        n_spikes_edit.blockSignals(prev_state)

        # Create and add GraphicsLayoutWidget
        glw = pg.GraphicsLayoutWidget(parent=self)
        # self.glw.useOpenGL(True)
        if "bgcolor" in self._theme:
            glw.setBackground(parse_color_str(self._theme["bgcolor"]))

        self.layout().addWidget(glw)
        self.wf_info = {}  # Will contain one dictionary for each line/channel label.
        for chan_state in self.chan_states:
            self.add_series(chan_state)

    def add_series(self, chan_state):
        glw = self.findChild(pg.GraphicsLayoutWidget)
        new_plot = glw.addPlot(row=len(self.wf_info), col=0, enableMenu=False)
        new_plot.setMouseEnabled(x=False, y=False)

        self.wf_info[chan_state['name']] = {
            'plot': new_plot,
            'line_ix': len(self.wf_info),
            'chan_id': chan_state['src']
        }

    def refresh_axes(self):
        for wf_key in self.wf_info:
            plot = self.wf_info[wf_key]['plot']
            plot.setXRange(self.plot_config['x_range'][0], self.plot_config['x_range'][1])
            plot.setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
            plot.hideAxis('bottom')
            plot.hideAxis('left')

    def clear(self):
        for line_label in self.wf_info:
            self.wf_info[line_label]['plot'].clear()

    def on_range_edit_editingFinished(self):
        range_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, name="range_LineEdit")
        self.plot_config['y_range'] = float(range_edit.text())
        self.refresh_axes()

    def on_n_spikes_edit_editingFinished(self):
        n_spikes_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, name="n_spikes_LineEdit")
        self.plot_config['n_waveforms'] = int(n_spikes_edit.text())
        self.refresh_axes()

    def parse_comments(self, comments):
        # comments is a list of lists: [[timestamp, string, rgba],]
        comment_strings = [x[1].decode('utf8') for x in comments]
        dtts = []
        for comm_str in comment_strings:
            if 'DTT:' in comm_str:
                dtts.append(float(comm_str[4:]))
        if len(dtts) > 0:
            new_dtt = dtts[-1]
            if not self.DTT or self.DTT != new_dtt:
                self.clear()
                self.DTT = new_dtt

    def update(self, line_label, data):
        """
        :param line_label: Label of the plot series
        :param data: Replace data in the plot with these data
        :return:
        """
        wfs, unit_ids = data
        x = (1000000 / self.samplingRate) * np.arange(wfs.shape[1]) + self.plot_config['x_range'][0]
        for ix in range(wfs.shape[0]):
            if np.sum(np.nonzero(wfs[ix])) > 0:
                c = pg.PlotCurveItem()
                pen_color = self._theme['pencolors'][unit_ids[ix]]
                c.setPen(pen_color)
                self.wf_info[line_label]['plot'].addItem(c)
                c.setData(x=x, y=self.plot_config['unit_scaling']*wfs[ix])
        data_items = self.wf_info[line_label]['plot'].listDataItems()
        if len(data_items) > self.plot_config['n_waveforms']:
            for di in data_items[:-self.plot_config['n_waveforms']]:
                self.wf_info[line_label]['plot'].removeItem(di)


class WaveformGUI(CustomGUI):
    widget_cls = WaveformWidget

    def __init__(self):
        self._plot_widget: WaveformWidget | None = None  # This will get updated in super init but it helps type hints
        super().__init__()
        self.setWindowTitle("Waveform")

    def parse_settings(self):
        super().parse_settings()

        if "plot" not in self._plot_settings:
            self._plot_settings["plot"] = {}

        for ini_path in self._settings_paths:
            settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

            settings.beginGroup("plot")
            for k, t in {
                "x_start": int, "x_stop": int, "y_range": int,
                "n_waveforms": int, "unit_scaling": float
            }.items():
                if k in settings.allKeys():
                    self._plot_settings["plot"][k] = settings.value(k, type=t)
            settings.endGroup()

            settings.beginGroup("theme")
            for k, t in {"frate_size": int}.items():
                if k in settings.allKeys():
                    self._theme_settings[k] = settings.value(k, type=t)
            settings.endGroup()

        super().parse_settings()

    def do_plot_update(self):
        for label in self._plot_widget.wf_info:
            this_info = self._plot_widget.wf_info[label]
            temp_wfs, unit_ids = self._data_source.get_waveforms(this_info)
            self._plot_widget.update(label, [temp_wfs, unit_ids])

        comments = self._data_source.get_comments()
        if comments:
            self._plot_widget.parse_comments(comments)

