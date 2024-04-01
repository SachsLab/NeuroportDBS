from matplotlib import cm
import numpy as np
from qtpy.QtWidgets import QGridLayout, QWidget, QVBoxLayout, QApplication
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QColor, QFont
import pyqtgraph as pg
from ..settings.defaults import THEMES, DEPTHRANGE, DEPTHTARGET, NPLOTSRAW


pen_colors = THEMES['dark']['pencolors']


# Plot settings dictionaries
DEFAULTPLOT = {
    'title': None,
    'x_label': None,
    'y_label': None,
    'x_ticks': False,
    'y_ticks': False,
    'x_axis': True,  # Is Visible
    'y_axis': True,
    'x_range': None,  # None for auto-scale, list otherwise
    'y_range': [0, 1],
    'y_tick_labels': None,
    'c_lim': [0, 1],
    'auto_scale': False,
    'interactive': True,
    'mouse_enabled': [False, False],
    'marker_line': DEPTHTARGET,
    'error_bars': False,
    'pen_color': QColor(255, 255, 255),
    # 'text_anchor': (2, 1),
    'text_anchor': (-.10, 0),
    # to get data
    'x_name': None,
    'y_name': None,
    'post_processing': None,
    'swap_xy': False,
    'image_plot': False
}
FEAT_VS_DEPTH = {**DEFAULTPLOT,
                 'x_range': DEPTHRANGE,
                 'y_ticks': True,
                 'interactive': True,
                 'auto_scale': True,
                 'mouse_enabled': [True, True],
                 'x_name': 'depth'}
DEPTH = {**DEFAULTPLOT,
         'x_range': [-5, 5],
         'x_axis': False,
         'y_range': DEPTHRANGE,
         'y_name': 'depth',
         'y_ticks': True,
         'interactive': True,
         'mouse_enabled': [False, True],
         'swap_xy': True,
         'text_anchor': (0.5, 2)}
SPECTRUM = {**DEFAULTPLOT,
            'x_range': DEPTHRANGE,
            'y_ticks': True,
            'interactive': False,
            'x_name': 'depth',
            'image_plot': True
            }


class BasePlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(BasePlotWidget, self).__init__(*args, **kwargs)
        self.plot_config = plot_config
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)
        self.plot = self.glw.addPlot(enableMenu=False)

        self.line = None
        self.text = None

        self.data = {}

        self.configure_plot()

    def leaveEvent(self, QEvent):
        self.clear_text_line()
        super().leaveEvent(QEvent)

    def clear_text_line(self):
        if self.line:
            self.line.setValue(-999999)
        if self.text:
            self.text.setText('')
            self.text.fill.setColor(QColor(0, 0, 0, 0))
        [x.setSymbolSize(6) for x in self.plot.curves]

    def configure_plot(self):
        self.plot.setTitle(title=self.plot_config["title"], **{"color": "w", "size": "16pt"})
        self.plot.hideButtons()

        if False and self.plot_config["image_plot"]:
            self.img = pg.ImageItem()
            self.plot.addItem(self.img)

            pos = np.array(self.plot_config["c_lim"])
            # color = np.array([[0, 0, 0, 255], self.plot_config["pen_color"].getRgb()], dtype=np.ubyte)
            # c_map = pg.ColorMap(pos, color)
            # lut = c_map.getLookupTable(pos[0], pos[1], 1024)

            colormap = cm.get_cmap("inferno")  # cm.get_cmap("CMRmap")
            colormap._init()
            lut = (colormap._lut * 255).view(np.ndarray)  # Convert matplotlib colormap from 0-1 to 0 -255 for Qt

            self.img.setLookupTable(lut)
            self.img.setLevels(pos)

            self.img.scale(1/1000, 1)
            self.img.setPos(DEPTHRANGE[0], 0)

        if self.plot_config["marker_line"] is not None:
            self.plot.addItem(pg.InfiniteLine(angle=0 if self.plot_config['swap_xy'] else 90,
                                              pos=self.plot_config['marker_line'],
                                              movable=False,
                                              pen='y'))
        self.plot.setMouseEnabled(x=self.plot_config['mouse_enabled'][0],
                                  y=self.plot_config['mouse_enabled'][1])
        # if mouse is enabled, a right click will bring the plot range to its default values
        self.plot.scene().sigMouseClicked.connect(self.mouse_clicked)
        self.plot.vb.installEventFilter(self)

        if self.plot_config["x_range"]:
            self.plot.setXRange(self.plot_config["x_range"][0], self.plot_config["x_range"][1], padding=0)
        if self.plot_config["y_range"]:
            self.plot.setYRange(self.plot_config["y_range"][0], self.plot_config["y_range"][1], padding=0)
        self.plot.setLabel("bottom", self.plot_config["x_label"])
        self.plot.setLabel("left", self.plot_config["y_label"])
        if not self.plot_config["x_axis"]:
            self.plot.hideAxis("bottom")
        if not self.plot_config["y_axis"]:
            self.plot.hideAxis("left")
        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)

        self.plot.getAxis('bottom').setStyle(showValues=self.plot_config["x_ticks"],
                                             tickFont=font, tickTextOffset=10)
        self.plot.getAxis('bottom').setTextPen((255, 255, 255, 255))

        self.plot.getAxis('left').setStyle(showValues=self.plot_config["y_ticks"],
                                           tickFont=font)
        self.plot.getAxis('left').setTextPen((255, 255, 255, 255))
        if self.plot_config['y_tick_labels']:
            self.plot.getAxis('left').setTicks(self.plot_config['y_tick_labels'])
        if self.plot_config['interactive']:
            self.plot.scene().sigMouseMoved.connect(self.mouse_moved)
            if self.plot_config['swap_xy']:
                self.line = pg.InfiniteLine(angle=0,
                                            pos=-9999,
                                            movable=False,
                                            pen='w')
            else:
                self.line = pg.InfiniteLine(angle=90,
                                            pos=-9999,
                                            movable=False,
                                            pen='w')
            self.line.setZValue(5)
            self.plot.addItem(self.line)

            self.text = pg.TextItem(text='', color='w', fill=(0, 0, 0, 0))
            self.text.setAnchor(self.plot_config['text_anchor'])
            self.text.setX(0)
            # self.text.setY(0.5)
            self.text.setY(0)
            self.plot.addItem(self.text)
            self.text.setZValue(6)

    def eventFilter(self, watched, event):
        # check if mouse scroll.
        # Normal scroll is Y axis zoom
        # CTRL + scroll is X axis zoom
        mods = QApplication.keyboardModifiers()
        if event.type() == QEvent.GraphicsSceneWheel:
            # no CTRL, Y axis enabled, do not block
            if mods != Qt.ControlModifier and self.plot_config['mouse_enabled'][1]:
                self.plot.setMouseEnabled(x=False,
                                          y=True)
                return False
            elif mods != Qt.ControlModifier and not self.plot_config['mouse_enabled'][1]:
                self.plot.setMouseEnabled(x=self.plot_config['mouse_enabled'][0],
                                          y=self.plot_config['mouse_enabled'][1])
                return True
            elif mods == Qt.ControlModifier and self.plot_config['mouse_enabled'][0]:
                self.plot.setMouseEnabled(x=True,
                                          y=False)
                return False
            elif mods == Qt.ControlModifier and not self.plot_config['mouse_enabled'][0]:
                self.plot.setMouseEnabled(x=self.plot_config['mouse_enabled'][0],
                                          y=self.plot_config['mouse_enabled'][1])
                return True

        self.plot.setMouseEnabled(x=self.plot_config['mouse_enabled'][0],
                                  y=self.plot_config['mouse_enabled'][1])
        return False

    def mouse_moved(self, evt):
        plot_coord = self.plot.vb.mapSceneToView(evt)
        closest = -99999
        value = None
        curves = [x for x in self.plot.curves if x.opts['symbol']]
        if self.plot_config['swap_xy']:
            y_ = [(x.yData[0], x.setSymbolSize(6))[0] for x in curves]

            if y_:
                closest = min(y_, key=lambda x: abs(x - plot_coord.y()))
                idx = y_.index(closest)
                value = curves[idx].xData[0]
                curves[idx].setSymbolSize(12)

                self.text.setY(closest)
                self.text.setX(0)
        else:
            # added unique since we can now have multiple points per x value
            x_ = [(np.unique(x.xData), x.setSymbolSize(6))[0] for x in curves]
            if x_:
                closest = min(x_, key=lambda x: abs(x - plot_coord.x()))[0]
                idx = x_.index(closest)
                value = curves[idx].yData[0]
                curves[idx].setSymbolSize(12)

                self.text.setX(min(self.plot.axes['bottom']['item'].range))
                # self.text.setX(closest)
                self.text.setY(max(self.plot.axes['left']['item'].range))
                # self.text.setY(value)

        self.line.setValue(closest)

        if value is not None:
            self.text.setText('x: ' + "{0:.3f}".format(closest) + '\n' + 'y: ' +
                              "{0:.3f}".format(value))
            self.text.fill.setColor(QColor(0, 0, 0, 175))

    def mouse_clicked(self, evt):
        if evt.button() == 2:
            if self.plot_config['auto_scale']:
                self.plot.autoRange(padding=0.05, items=self.plot.dataItems)
                if self.plot_config['x_range']:
                    self.plot.setXRange(self.plot_config["x_range"][0], self.plot_config["x_range"][1],
                                        padding=0)
            else:
                if self.plot_config["x_range"]:
                    self.plot.setXRange(self.plot_config["x_range"][0], self.plot_config["x_range"][1], padding=0)
                if self.plot_config["y_range"]:
                    self.plot.setYRange(self.plot_config["y_range"][0], self.plot_config["y_range"][1], padding=0)

    def update_plot(self, all_data):
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, np array of data]}
            for idx, data in all_data.items():
                # append data
                x = data[self.plot_config["x_name"]] if self.plot_config["x_name"] in data else None

                if x not in [None, ''] and self.plot_config["y_name"] in data:
                    y = data[self.plot_config["y_name"]]

                    # if depth data was overwritten, we need to delete previous points and errorbars
                    if x in self.data.keys():
                        items = self.plot.items
                        for i in items:
                            if type(i) is pg.PlotDataItem:
                                if any(i.xData == x):
                                    self.plot.removeItem(i)
                            if type(i) is pg.ErrorBarItem:
                                if i.opts['x'][0] == x:
                                    self.plot.removeItem(i)

                    self.data[x] = y

                    if y[2]:
                        symbol_brush = self.plot_config["pen_color"]
                    else:
                        symbol_brush = None

                    # post_processing receives the entire feature value array, typically:
                    # [x, y, valid].
                    # should return an array with values to plot
                    if self.plot_config["post_processing"] and not self.plot_config["error_bars"]:
                        y = self.plot_config["post_processing"](x, y)
                    elif self.plot_config["post_processing"] and self.plot_config["error_bars"]:
                        y, eb = self.plot_config["post_processing"](x, y)
                        self.plot.addItem(pg.ErrorBarItem(x=[x], y=y, height=eb, pen=self.plot_config["pen_color"]))
                    else:
                        y = y[1]

                    if not self.plot_config["image_plot"]:
                        # make sure x is a list the same size as y
                        x = [x] * len(y)

                        self.plot.plot(x=x, y=y, symbol='o', symbolSize=6, pen=None,
                                       symbolBrush=symbol_brush, symbolPen=self.plot_config["pen_color"])
                    else:
                        self.img.setImage(y, autoLevels=False)

                    if self.plot_config['auto_scale']:
                        self.plot.autoRange(padding=0.05, items=self.plot.dataItems)
                        if self.plot_config["x_range"]:
                            self.plot.setXRange(self.plot_config["x_range"][0], self.plot_config["x_range"][1],
                                                padding=0)
                        # self.plot.enableAutoRange(axis=pg.ViewBox.YAxis)

    def clear_plot(self):
        # rms settings
        self.plot.clear()
        self.configure_plot()
        self.data = {}


class NullPlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(NullPlotWidget, self).__init__(*args, **kwargs)
        self.plot_config = plot_config

    def update_plot(self, all_data):
        pass

    def clear_plot(self):
        pass


class RawPlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(RawPlots, self).__init__(*args, **kwargs)

        self.plot_config = plot_config

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # create GLW for the depth plot
        depth_sett = {**DEPTH,
                      'pen_color': self.plot_config["pen_color"]}
        self.depth_plot = BasePlotWidget(depth_sett)
        self.layout.addWidget(self.depth_plot, 0, 0, NPLOTSRAW, 1)

        # extra depth_plot settings
        self.depth_plot.plot.invertY()
        self.fill_bar = self.depth_plot.plot.plot([-5, 5],
                                             [depth_sett['y_range'][0], depth_sett['y_range'][0]],
                                             fillLevel=depth_sett['y_range'][0], brush=(255, 255, 255, 100),
                                             movable=True)
        self.fill_bar_position = []
        self.depth_bar = pg.InfiniteLine(angle=0,
                                         # bounds=[depth_sett['y_range'][0],
                                         #        depth_sett['y_range'][1]],
                                         pos=depth_sett['y_range'][0],
                                         movable=True,
                                         pen='w')
        self.depth_bar.sigDragged.connect(self.depth_bar_drag)
        self.depth_plot.plot.addItem(self.depth_bar)
        self.depth_text = pg.TextItem(text='', color='w', fill=(0, 0, 0, 0))
        self.depth_text.setAnchor((.5, 1.5))
        self.depth_plot.plot.addItem(self.depth_text)
        self.depth_text.setZValue(1)

        # Prepare plot data
        self.data_layout = QVBoxLayout()
        self.data_layout.setContentsMargins(0, 0, 0, 0)
        self.data_layout.setSpacing(0)
        self.layout.addLayout(self.data_layout, 0, 1, NPLOTSRAW, 5)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 5)

        self.data_figures = []
        self.depth_pdi = {}  # all depth data

        self.data_texts = []

        raw_sett = {**DEFAULTPLOT,
                    'x_axis': False,  # Is Visible
                    'y_axis': False,
                    'x_range': [self.plot_config["x_start"], self.plot_config["x_stop"]],  # self.plot_config['x_range'],  # None for auto-scale, list otherwise
                    'y_range': [-self.plot_config["y_range"], self.plot_config["y_range"]],
                    'auto_scale': False,
                    'interactive': False,
                    'marker_line': None,
                    'error_bars': False
                    }
        for i in range(NPLOTSRAW):
            tmp = BasePlotWidget(raw_sett)
            self.data_layout.addWidget(tmp)
            self.data_figures.append(tmp)
            tmp_txt = pg.TextItem(text="", angle=90, color='w')
            tmp_txt.setX(0)
            tmp_txt.setY(0)
            tmp_txt.setAnchor((0.5, 1))
            tmp_txt.setZValue(100)
            _font = QFont()
            _font.setPointSizeF(8.5)
            tmp_txt.setFont(_font)
            tmp.plot.addItem(tmp_txt)
            self.data_texts.append(tmp_txt)

    def depth_bar_drag(self):
        # hide text field
        self.depth_plot.clear_text_line()

        # set fill area to be the first 8 depths found above the line
        all_depths = np.sort([x for x in self.depth_pdi.keys()])
        if len(all_depths) > 0:
            curr_value = self.depth_bar.value()
            diffs = abs(all_depths - curr_value)

            # lock to closest depth value
            idx, = np.where(diffs == min(diffs))[0]
            self.depth_bar.setValue(all_depths[idx])
            self.plot_depth_values()

    # Update plot is only for new datum
    def update_plot(self, all_data):
        # new_depth = -20
        new_depth = DEPTHRANGE[0]
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, np array of data]}
            for _, depth_data in all_data.items():
                # append data
                if depth_data[0] not in self.depth_pdi.keys():
                    # instead of saving Plot Data Item, save the data
                    self.depth_pdi[depth_data[0]] = depth_data[1]
                else:
                    # overwritten depth data
                    if not all(depth_data[1] == self.depth_pdi[depth_data[0]]):
                        self.depth_pdi[depth_data[0]] = depth_data[1]

                # plot depth
                symbol_brush = self.plot_config["pen_color"] if depth_data[2] else None
                self.depth_plot.plot.plot(x=[0], y=[depth_data[0]], symbol='o', symbolBrush=symbol_brush,
                                          symbolPen=self.plot_config["pen_color"], symbolSize=6)

                if new_depth == DEPTHRANGE[0] and new_depth > depth_data[0]:
                    new_depth = depth_data[0]
                else:
                    new_depth = max(depth_data[0], new_depth)

            # move draggable bar to new depth
            self.depth_bar.setValue(new_depth)
            self.plot_depth_values()

    def plot_depth_values(self):
        # get current index of selected depth
        all_depths = np.sort([x for x in self.depth_pdi.keys()])
        curr_value = self.depth_bar.value()

        idx, = np.where(all_depths == curr_value)[0]

        # plot last 8 depth data
        # make fill bar around 8 depths above the currently selected one
        top_idx = max(0, idx - (NPLOTSRAW-1))
        self.fill_bar.setData(x=[-5, 5], y=[all_depths[idx], all_depths[idx]], fillLevel=all_depths[top_idx])

        plot_idx = 1
        while plot_idx <= NPLOTSRAW:
            if idx >= top_idx:
                to_plot = self.depth_pdi[all_depths[idx]]  # data
                if len(self.data_figures[-plot_idx].plot.dataItems) == 0:
                    self.data_figures[-plot_idx].plot.addItem(pg.PlotDataItem(to_plot,
                                                              pen=self.plot_config["pen_color"],
                                                              autoDownsample=True))
                else:
                    self.data_figures[-plot_idx].plot.dataItems[0].setData(to_plot)

                self.data_texts[-plot_idx].setText("{0:.3f}".format(all_depths[idx]))
            else:
                self.data_texts[-plot_idx].setText("")
                if len(self.data_figures[-plot_idx].plot.dataItems) > 0:
                    self.data_figures[-plot_idx].plot.dataItems[0].setData([0])

            self.data_figures[-plot_idx].plot.setYRange(-self.plot_config["y_range"], self.plot_config["y_range"])

            idx -= 1
            plot_idx += 1

    def clear_plot(self):
        self.depth_pdi = {}

        # clear depth plot
        # self.depth_bar.setValue(-20)
        self.depth_bar.setValue(DEPTHRANGE[0])
        self.fill_bar.setData(x=[-5, 5],
                              y=[DEPTHRANGE[0], DEPTHRANGE[0]],
                              fillLevel=DEPTHRANGE[0])

        for it in self.depth_plot.plot.listDataItems():
            if it.opts['symbol'] == 'o':
                self.depth_plot.plot.removeItem(it)

        # clear data plots
        [x.plot.removeItem(x.plot.dataItems[0]) for x in self.data_figures if x.plot.dataItems]

        for txt in self.data_texts:
            txt.setText("")


class STNPlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(STNPlots, self).__init__(*args, **kwargs)
        self.plot_config = plot_config

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        rms_sett = {**FEAT_VS_DEPTH,
                    'title': 'Noise RMS (' + u'\u03BC' + 'V)',
                    'y_name': 'NoiseRMS',
                    'pen_color': self.plot_config["pen_color"]}
        self.rms_plot = BasePlotWidget(rms_sett)
        self.layout.addWidget(self.rms_plot, 0, 0, 1, 1)

        beta_sett = {**FEAT_VS_DEPTH,
                     'title': 'Beta power (dB)',
                     'y_name': 'BetaPower',
                     'post_processing': self.beta_process,
                     'pen_color': self.plot_config["pen_color"]}
        self.bp_plot = BasePlotWidget(beta_sett)
        self.layout.addWidget(self.bp_plot, 1, 0, 1, 1)
        # https://gist.github.com/beniwohli/765262
        pac_sett = {**FEAT_VS_DEPTH,
                    'title': 'Peak ' + u'\u03B2' + '-' + u'\u03B3' + ' PAC (± var)',
                    'y_name': 'PAC',
                    'y_range': [-.1, 1],
                    'x_ticks': True,
                    'post_processing': self.pac_process,
                    'error_bars': True,
                    'pen_color': self.plot_config["pen_color"]}
        self.pac_plot = BasePlotWidget(pac_sett)
        self.layout.addWidget(self.pac_plot, 2, 0, 1, 1)

        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)

    @staticmethod
    def beta_process(x, data):
        return 10 * np.log10(data[1])

    @staticmethod
    def pac_process(x, data):
        # data contains peak, mean, variance
        return data[1][:1], data[1][-1:]

    def update_plot(self, all_data):
        self.rms_plot.update_plot(all_data)
        self.bp_plot.update_plot(all_data)
        self.pac_plot.update_plot(all_data)

    def clear_plot(self):
        self.rms_plot.clear_plot()
        self.bp_plot.clear_plot()
        self.pac_plot.clear_plot()


class LFPPlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(LFPPlots, self).__init__(*args, **kwargs)

        self.plot_config = plot_config

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        pwr_sett = {**SPECTRUM,
                    'title': 'Power Spectrum (depth vs frequency; dB)',
                    'x_ticks': False,
                    'x_name': 'depth',
                    'y_name': 'LFPSpectrumAndEpisodes',
                    'y_range': [0, 21],
                    'y_tick_labels': [[(1, 4), (6, 8), (11, 16), (16, 32), (21, 64), (26, 128), (31, 256)]],
                    'c_lim': [50, 150],
                    'post_processing': self.spectrum_process,
                    'pen_color': self.plot_config["pen_color"]
                    }
        self.spectro_plot = BasePlotWidget(pwr_sett)
        self.layout.addWidget(self.spectro_plot, 0, 0, 1, 1)

        beta_sett = {**FEAT_VS_DEPTH,
                     'interactive': True,
                     'title': 'Beta power (dB)',
                     'y_name': 'LFPSpectrumAndEpisodes',
                     'post_processing': self.beta_process,
                     'pen_color': self.plot_config["pen_color"]}
        self.bp_plot = BasePlotWidget(beta_sett)
        self.layout.addWidget(self.bp_plot, 1, 0, 1, 1)

        pep_sett = {**SPECTRUM,
                    'title': 'P_episodes (depth vs frequency; %)',
                    'x_ticks': False,
                    'x_name': 'depth',
                    'y_name': 'LFPSpectrumAndEpisodes',
                    'y_range': [0, 21],
                    'y_tick_labels': [[(1, 4), (6, 8), (11, 16), (16, 32), (21, 64)]],
                    'c_lim': [0, 1],
                    'post_processing': self.episodes_process,
                    'pen_color': self.plot_config["pen_color"]
                    }
        self.episodes_plot = BasePlotWidget(pep_sett)
        self.layout.addWidget(self.episodes_plot, 2, 0, 1, 1)

        beta_ep_sett = {**FEAT_VS_DEPTH,
                        'x_ticks': True,
                        'interactive': True,
                        'title': 'Beta episodes',
                        'y_name': 'LFPSpectrumAndEpisodes',
                        'post_processing': self.beta_ep_process,
                        'pen_color': self.plot_config["pen_color"]}
        self.b_ep_plot = BasePlotWidget(beta_ep_sett)
        self.layout.addWidget(self.b_ep_plot, 3, 0, 1, 1)

        # self.layout.addWidget(QLabel(), 4, 0, 1, 1)
        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)
        self.layout.setRowStretch(3, 1)

        # 0.001 mm steps
        self.spectrum_x = np.arange(pwr_sett['x_range'][0] * 1000,
                                    pwr_sett['x_range'][1] * 1000, 1, dtype=int)
        self.spectrum_depths = np.array(np.round(pwr_sett['x_range'][0]*1000), dtype=int)
        self.spectrum_data = np.zeros((pwr_sett['y_range'][1], self.spectrum_x.shape[0]))

        self.episodes_depths = np.array(np.round(pep_sett['x_range'][0] * 1000), dtype=int)
        self.episodes_data = np.zeros((pep_sett['y_range'][1], self.spectrum_x.shape[0]))

        self.depth_data = {}

    def spectrum_process(self, x, data):
        # data is a chan x values array where n values=62 representing 31 power frequency points and 31 p_episode points
        new_depth = np.round(x*1000)
        new_values = 10 * np.log10(data[1][:data[0].shape[0]])
        new_values = new_values[:21]  # limit to 64 Hz

        prev_depths = self.spectrum_depths[self.spectrum_depths < new_depth]
        if prev_depths.shape[0] > 0:
            prev_depth = prev_depths.max()
            prev_values = self.spectrum_data[:, self.spectrum_x == prev_depth].flatten()

            depth_diff = new_depth - prev_depth
            values_diff = new_values - prev_values

            delta = np.arange(0, depth_diff + 1, 1) / depth_diff

            self.spectrum_data[:, np.logical_and(self.spectrum_x >= prev_depth, self.spectrum_x <= new_depth)] = \
                np.add(np.atleast_2d(prev_values).T, (np.atleast_2d(values_diff).T * delta))
        else:
            prev_depth = DEPTHRANGE[0]  # -20.000

        next_depths = self.spectrum_depths[self.spectrum_depths > new_depth]
        if next_depths.shape[0] > 0:
            next_depth = next_depths.min()
            next_values = self.spectrum_data[:, self.spectrum_x == next_depth].flatten()

            depth_diff = next_depth - new_depth
            values_diff = next_values - new_values

            delta = np.arange(0, depth_diff + 1, 1) / depth_diff

            self.spectrum_data[:, np.logical_and(self.spectrum_x >= new_depth, self.spectrum_x <= next_depth)] = \
                np.add(np.atleast_2d(new_values).T, (np.atleast_2d(values_diff).T * delta))

        # append new depth
        self.spectrum_depths = np.insert(self.spectrum_depths,
                                         np.where(self.spectrum_depths == prev_depth)[0] + 1,
                                         new_depth)

        return self.spectrum_data.T

    @staticmethod
    def beta_ep_process(x, data):
        new_values = data[1][data[0].shape[0]:]
        ep = np.mean(new_values[np.logical_and(data[0] >= 13, data[0] <= 30)])
        return [ep]

    @staticmethod
    def beta_process(x, data):
        new_values = data[1][:data[0].shape[0]]
        pwr = np.mean(new_values[np.logical_and(data[0] >= 13, data[0] <= 30)])
        return [np.log10(pwr)]

    def episodes_process(self, x, data):
        # data is a chan x values array where n values=62 representing 31 power frequency points and 31 p_episode points
        new_depth = np.round(x*1000)
        new_values = data[1][data[0].shape[0]:]
        new_values = new_values[:21]
        # new_values = 10*np.log10(data[1][:data[0].shape[0]])

        prev_depths = self.episodes_depths[self.episodes_depths < new_depth]
        if prev_depths.shape[0] > 0:
            prev_depth = prev_depths.max()
            prev_values = self.episodes_data[:, self.spectrum_x == prev_depth].flatten()

            depth_diff = new_depth - prev_depth
            values_diff = new_values - prev_values

            delta = np.arange(0, depth_diff + 1, 1) / depth_diff

            self.episodes_data[:, np.logical_and(self.spectrum_x >= prev_depth, self.spectrum_x <= new_depth)] = \
                np.add(np.atleast_2d(prev_values).T, (np.atleast_2d(values_diff).T * delta))
        else:
            prev_depth = DEPTHRANGE[0]  # -20.000

        next_depths = self.episodes_depths[self.episodes_depths > new_depth]
        if next_depths.shape[0] > 0:
            next_depth = next_depths.min()
            next_values = self.episodes_data[:, self.spectrum_x == next_depth].flatten()

            depth_diff = next_depth - new_depth
            values_diff = next_values - new_values

            delta = np.arange(0, depth_diff + 1, 1) / depth_diff

            self.episodes_data[:, np.logical_and(self.spectrum_x >= new_depth, self.spectrum_x <= next_depth)] = \
                np.add(np.atleast_2d(new_values).T, (np.atleast_2d(values_diff).T * delta))

        # append new depth
        self.episodes_depths = np.insert(self.episodes_depths,
                                         np.where(self.episodes_depths == prev_depth)[0] + 1,
                                         new_depth)

        return self.episodes_data.T

    def update_plot(self, all_data):
        self.spectro_plot.update_plot(all_data)
        self.bp_plot.update_plot(all_data)
        self.episodes_plot.update_plot(all_data)
        self.b_ep_plot.update_plot(all_data)

    def clear_plot(self):
        self.spectro_plot.clear_plot()
        self.bp_plot.clear_plot()
        self.episodes_plot.clear_plot()
        self.b_ep_plot.clear_plot()

        self.depth_data = {}


class SpikePlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(SpikePlots, self).__init__(*args, **kwargs)

        self.plot_config = plot_config

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # rms settings
        rms_sett = {**FEAT_VS_DEPTH,
                    'title': 'Noise RMS (' + u'\u03BC' + 'V)',
                    'y_name': 'DBSSpikeFeatures',
                    'post_processing': lambda x,y : [y[1][0]],
                    'pen_color': self.plot_config["pen_color"]}

        self.rms_plot = BasePlotWidget(rms_sett)
        self.layout.addWidget(self.rms_plot, 0, 0, 1, 1)

        # rate
        rate_sett = {**FEAT_VS_DEPTH,
                     'title': 'Rate (Hz)',
                     'y_name': 'DBSSpikeFeatures',
                     'post_processing': lambda x, y: [y[1][1]],
                     'pen_color': self.plot_config["pen_color"]}

        self.rate_plot = BasePlotWidget(rate_sett)
        self.layout.addWidget(self.rate_plot, 1, 0, 1, 1)

        # rate
        burst_sett = {**FEAT_VS_DEPTH,
                      'title': 'Burst Index',
                      'y_name': 'DBSSpikeFeatures',
                      'post_processing': lambda x, y: [y[1][2]],
                      'pen_color': self.plot_config["pen_color"]}

        self.burst_plot = BasePlotWidget(burst_sett)
        self.layout.addWidget(self.burst_plot, 2, 0, 1, 1)

        # FF
        ff_sett = {**FEAT_VS_DEPTH,
                   'title': 'Fano Factor',
                   'x_ticks': True,
                   'y_name': 'DBSSpikeFeatures',
                   'post_processing': lambda x, y: [y[1][3]],
                   'pen_color': self.plot_config["pen_color"]}

        self.ff_plot = BasePlotWidget(ff_sett)
        self.layout.addWidget(self.ff_plot, 3, 0, 1, 1)

        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)
        self.layout.setRowStretch(3, 1)

        self.depth_data = {}

    def update_plot(self, all_data):
        self.rms_plot.update_plot(all_data)
        self.rate_plot.update_plot(all_data)
        self.burst_plot.update_plot(all_data)
        self.ff_plot.update_plot(all_data)

    def clear_plot(self):
        # rms settings
        self.rms_plot.clear_plot()
        self.rate_plot.clear_plot()
        self.burst_plot.clear_plot()
        self.ff_plot.clear_plot()

        self.depth_data = {}


class MappingPlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(MappingPlots, self).__init__(*args, **kwargs)
        self.plot_config = plot_config

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the Kinesthetic
        kin_sett = {**FEAT_VS_DEPTH,
                    'title': 'Kinesthetic Response',
                    'y_name': 'Kinesthetic',
                    'y_range': [-.1, 6.1],
                    'y_tick_labels': [[(0, "No"), (1, "Un"), (2, "Fo"), (3, "Le"), (4, "Ha"), (5, "Ar"), (6, 'He')]],
                    'auto_scale': False,
                    'post_processing': self.fill_empty,
                    'pen_color': self.plot_config["pen_color"]}
        self.kin_plot = BasePlotWidget(kin_sett)
        self.add_dashed_lines(self.kin_plot.plot)
        self.layout.addWidget(self.kin_plot, 0, 0, 1, 1)

        tact_sett = {**FEAT_VS_DEPTH,
                     'title': 'Tactile Response',
                     'y_name': 'Tactile',
                     'y_range': [-.1, 6.1],
                     'y_tick_labels': [[(0, "No"), (1, "Un"), (2, "Fo"), (3, "Le"), (4, "Ha"), (5, "Ar"), (6, 'He')]],
                     'auto_scale': False,
                     'post_processing': self.fill_empty,
                     'pen_color': self.plot_config["pen_color"]}
        self.tact_plot = BasePlotWidget(tact_sett)
        self.add_dashed_lines(self.tact_plot.plot)
        self.layout.addWidget(self.tact_plot, 1, 0, 1, 1)

        custom_sett = {**FEAT_VS_DEPTH,
                       'title': 'Custom Response',
                       'y_name': 'Custom',
                       'y_range': [-.1, 6.1],
                       'y_tick_labels': [[(0, "No"), (1, "Un"), (2, "Fo"), (3, "Le"), (4, "Ha"), (5, "Ar"), (6, 'He')]],
                       'auto_scale': False,
                       'post_processing': self.fill_empty,
                       'pen_color': self.plot_config["pen_color"]}
        self.custom_plot = BasePlotWidget(custom_sett)
        self.add_dashed_lines(self.custom_plot.plot)
        self.layout.addWidget(self.custom_plot, 2, 0, 1, 1)

        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)

    @staticmethod
    def add_dashed_lines(plot):
        # add separators for head, ul, ll,
        plot.addItem(pg.InfiniteLine(angle=0,
                                     pos=5.5,
                                     movable=False,
                                     pen=pg.mkPen('w', width=0.5, style=Qt.DashLine)))

        plot.addItem(pg.InfiniteLine(angle=0,
                                     pos=3.5,
                                     movable=False,
                                     pen=pg.mkPen('w', width=0.5, style=Qt.DashLine)))

        plot.addItem(pg.InfiniteLine(angle=0,
                                     pos=1.5,
                                     movable=False,
                                     pen=pg.mkPen('w', width=0.5, style=Qt.DashLine)))

    @staticmethod
    def fill_empty(x, data):
        if len(data[1]) == 0:
            data[1] = [0]
        return data[1]

    def update_plot(self, all_data):
        self.kin_plot.update_plot(all_data)
        self.tact_plot.update_plot(all_data)
        self.custom_plot.update_plot(all_data)

    def clear_plot(self):
        self.kin_plot.clear_plot()
        self.tact_plot.clear_plot()
        self.custom_plot.clear_plot()
        self.add_dashed_lines(self.kin_plot.plot)
        self.add_dashed_lines(self.tact_plot.plot)
        self.add_dashed_lines(self.custom_plot.plot)
