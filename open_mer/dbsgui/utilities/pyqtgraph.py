import pyqtgraph as pg
import pyqtgraph.colormap
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
import numpy as np


color_sets = list(Gradients.keys()) + pyqtgraph.colormap.listMaps('matplotlib')


def parse_color_str(color_str: str):
    _col = color_str.replace("'", "")
    if len(color_str) > 1:
        if color_str == 'black':
            _col = 'k'
        elif color_str[0] in ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w']:
            _col = color_str[0]
    return _col


def str2rgb(color_str: str):
    from pyqtgraph.functions import mkColor
    _col = parse_color_str(color_str)
    _col = mkColor(_col).getRgb()
    return np.array(_col)[None, :]


def make_qcolor(input_color):
    from qtpy import QtGui
    pen_color = input_color
    if isinstance(pen_color, np.ndarray):
        pen_color = pen_color.tolist()
    if isinstance(pen_color, list):
        pen_color = QtGui.QColor(*pen_color)
    else:
        pen_color = QtGui.QColor(pen_color)
    return pen_color


def get_colormap(color_set, n_items):
    if color_set == 'random':
        colors = np.random.uniform(size=(n_items, 3), low=.5, high=.9)
        colors = pg.ColorMap(np.arange(n_items) / max(n_items - 1, 1), (255 * colors).astype(int))
    elif color_set in Gradients:
        colors = pg.ColorMap(*zip(*Gradients[color_set]["ticks"]))
    elif color_set in pg.colormap.listMaps('matplotlib'):
        colors = pg.colormap.get(color_set, source='matplotlib', skipCache=True)
    else:
        # Solid color
        _rgb = str2rgb(color_set)
        colors = pg.ColorMap(np.arange(n_items) / max(n_items - 1, 1), np.repeat(_rgb, n_items, axis=0))
    color_map = colors.getLookupTable(nPts=n_items)
    return color_map
