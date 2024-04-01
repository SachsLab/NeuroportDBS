import numpy as np
from qtpy import QtCore, QtGui
import pyqtgraph as pg
from ..dbsgui.utilities.pyqtgraph import parse_color_str, get_colormap
from ..dbsgui.widgets.custom import CustomGUI, CustomWidget
from ..data_source import get_now_time


class RasterWidget(CustomWidget):
    frate_changed = QtCore.Signal(str, float)

    def __init__(self, *args, theme={}, plot={}):
        self.DTT = None
        self._plot_config = {}
        super().__init__(*args, theme=theme, plot=plot)

    def _parse_config(self, theme={}, plot={}):
        super()._parse_config(theme=theme)
        plot = plot["plot"]
        self._plot_config["x_range"] = plot.get("x_range", 0.5)
        self._plot_config["y_range"] = plot.get("y_range", 8)

    def create_plots(self):
        # Create and add GraphicsLayoutWidget
        glw = pg.GraphicsLayoutWidget(parent=self)
        # glw.useOpenGL(True)
        if 'bgcolor' in self._theme:
            glw.setBackground(parse_color_str(self._theme['bgcolor']))
        self.layout().addWidget(glw)

        self.rasters = {}  # Will contain one dictionary for each line/channel label.
        for chan_state in self.chan_states:
            self.add_series(chan_state)

    def add_series(self, chan_state):
        my_theme = self._theme
        glw = self.findChild(pg.GraphicsLayoutWidget)
        new_plot = glw.addPlot(row=len(self.rasters), col=0, enableMenu=False)
        new_plot.setMouseEnabled(x=False, y=False)

        # Appearance settings
        self._theme["color_iterator"] = (self._theme["color_iterator"] + 1) % len(my_theme["pencolors"])
        pen_color = QtGui.QColor(my_theme["pencolors"][self._theme["color_iterator"]])
        pen = pg.mkPen(pen_color, width=my_theme.get("linewidth", 1))
        # Create PlotCurveItem for latest spikes (bottom row) and slower-updating old spikes (upper rows)
        pcis = []
        for pci_ix in range(2):
            pci = pg.PlotCurveItem(parent=new_plot, connect="pairs")
            pci.setPen(pen)
            new_plot.addItem(pci)
            pcis.append(pci)
        # Create text for displaying firing rate. Placeholder text is channel label.
        frate_annotation = pg.TextItem(text=chan_state["name"],
                                       color=(255, 255, 255))
        frate_annotation.setPos(0, self._plot_config["y_range"])
        my_font = QtGui.QFont()
        my_font.setPointSize(my_theme.get("frate_size", 24))
        frate_annotation.setFont(my_font)
        new_plot.addItem(frate_annotation)
        # Store information
        self.rasters[chan_state['name']] = {
            'plot': new_plot,
            'old': pcis[0],
            'latest': pcis[1],
            'line_ix': len(self.rasters),
            'chan_id': chan_state['src'],
            'frate_item': frate_annotation
        }
        self.clear()

    def refresh_axes(self):
        self.x_lim = int(self._plot_config['x_range'] * self.samplingRate)
        for rs_key in self.rasters:
            plot = self.rasters[rs_key]['plot']
            plot.setXRange(0, self._plot_config['x_range'] * self.samplingRate)
            plot.setYRange(-0.05, self._plot_config['y_range'] + 0.05)
            plot.hideAxis('bottom')
            plot.hideAxis('left')

    def clear(self):
        start_time = int(get_now_time())
        for key in self.rasters:
            rs = self.rasters[key]
            rs['old'].clear()
            rs['latest'].clear()
            rs['old_timestamps'] = np.empty(0, dtype=np.uint32)  # Row 1 to top row
            rs['latest_timestamps'] = np.empty(0, dtype=np.uint32)  # Bottom row
            rs['count'] = 0
            rs['start_time'] = start_time
            rs['r0_tmin'] = start_time - (start_time % (self._plot_config['x_range'] * self.samplingRate))
            rs['last_spike_time'] = start_time
            self.modify_frate(key, 0)

    def modify_frate(self, rs_key, new_frate):
        self.rasters[rs_key]['frate'] = new_frate
        new_label = "{0:3.0f}".format(new_frate)
        self.rasters[rs_key]['frate_item'].setText(new_label)
        self.frate_changed.emit(rs_key, new_frate)

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

        :param line_label: Label of the segmented series
        :param data: Replace data in the segmented series with these data
        :return:
        """
        rs = self.rasters[line_label]  # A dictionary of info unique to each channel

        # Calculate timestamp of last sample in bottom row
        now_time = int(get_now_time())
        new_r0_tmin = now_time - (now_time % self.x_lim)

        # Process data
        data = np.uint32(np.concatenate(data))  # For now, put all sorted units into the same unit.
        data = data[data > rs['last_spike_time']]  # Only keep spikes we haven't seen before.
        rs['count'] += data.size
        if data.size > 0:
            rs['last_spike_time'] = max(data)

        # Add new spikes into the bottom row (== latest_timestamps)
        rs['latest_timestamps'] = np.append(rs['latest_timestamps'], data)

        # Move spikes that do not belong in the bottom row to the upper section (latest)
        b_move_old = rs['latest_timestamps'] < new_r0_tmin
        if np.any(b_move_old):
            rs['old_timestamps'] = np.append(rs['old_timestamps'], rs['latest_timestamps'][b_move_old])
            rs['latest_timestamps'] = rs['latest_timestamps'][np.logical_not(b_move_old)]

        # Remove spikes from rs['old_timestamps'] that are outside the plot_range
        new_tmin = new_r0_tmin - self.x_lim * (self._plot_config['y_range'] - 1)
        b_drop_old = rs['old_timestamps'] < new_tmin
        if np.any(b_drop_old):
            rs['old_timestamps'] = rs['old_timestamps'][np.logical_not(b_drop_old)]
            rs['count'] -= np.sum(b_drop_old)

        # Update bottom section of plot (latest)
        if (data.size > 0) or np.any(b_move_old) or (new_r0_tmin != rs['r0_tmin']):
            x_vals = np.repeat(rs['latest_timestamps'] - new_r0_tmin, 2)
            y_vals = 0.1 * np.ones_like(x_vals)
            y_vals[1::2] += 0.8
            rs['latest'].setData(x=x_vals, y=y_vals)

        # Update upper section of plot (old)
        if np.any(b_move_old) or np.any(b_drop_old) or (new_r0_tmin != rs['r0_tmin']):
            # Get x- and y-vals as though all spikes are to be plotted on second-from-bottom row.
            x_vals = rs['old_timestamps'] % self.x_lim
            y_vals = 1.1 * np.ones_like(x_vals)  # second-from-bottom starts at y=1.1
            # If a spike is older than row_ix, += 1
            for row_ix in range(1, self._plot_config['y_range']):
                row_cutoff = new_r0_tmin - (row_ix * self.x_lim)
                y_vals[rs['old_timestamps'] < row_cutoff] += 1
            x_vals = np.repeat(x_vals, 2)
            y_vals = np.repeat(y_vals, 2)
            y_vals[1::2] += 0.8
            rs['old'].setData(x=x_vals, y=y_vals)

        # Update some stored variables
        # r0_tmin is used to determine if we need to make a new row.
        rs['r0_tmin'] = new_r0_tmin
        # start_time is the newer between when we started getting spikes in this area,
        # and what the oldest spike is in this plot.
        rs['start_time'] = max(rs['start_time'], new_tmin)

        # Update frate annotation.
        samples_elapsed = max(now_time, rs['last_spike_time']) - rs['start_time']
        if samples_elapsed > 0:
            frate = rs['count'] * self.samplingRate / samples_elapsed
            self.modify_frate(line_label, frate)


class RasterGUI(CustomGUI):
    widget_cls = RasterWidget

    def __init__(self):
        self._plot_widget: RasterWidget | None = None  # This will get updated in super init but it helps type hints
        super(RasterGUI, self).__init__()
        self.setWindowTitle("Raster")

    def parse_settings(self):
        super().parse_settings()

        if "plot" not in self._plot_settings:
            self._plot_settings["plot"] = {}

        for ini_path in self._settings_paths:
            settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

            settings.beginGroup("plot")
            for k, t in {"x_range": float, "y_range": int}.items():
                if k in settings.allKeys():
                    self._plot_settings["plot"][k] = settings.value(k, type=t)
            settings.endGroup()

            settings.beginGroup("theme")
            for k, t in {"frate_size": int}.items():
                if k in settings.allKeys():
                    self._theme_settings[k] = settings.value(k, type=t)
            settings.endGroup()

    def do_plot_update(self):
        ev_timestamps = self._data_source.get_event_data()
        ev_chan_ids = [x[0] for x in ev_timestamps]
        for chan_label in self._plot_widget.rasters:
            ri = self._plot_widget.rasters[chan_label]
            if ri['chan_id'] in ev_chan_ids:
                data = ev_timestamps[ev_chan_ids.index(ri['chan_id'])][1]['timestamps']
            else:
                data = [[], ]
            self._plot_widget.update(chan_label, data)

        comments = self._data_source.get_comments()
        if comments:
            self._plot_widget.parse_comments(comments)
