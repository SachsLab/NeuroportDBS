import sys
import qtpy
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy.QtGui import *
import numpy as np
import pyqtgraph as pg
from pympler import tracker

NSAMPLES = 100000


class MyGUI(QMainWindow):
    def __init__(self):
        super(MyGUI, self).__init__()
        self.setup_ui()
        self.show()
        self.tr = tracker.SummaryTracker()
        self.loop_count = 0

    def setup_ui(self):
        self.resize(800, 600)
        self.setCentralWidget(QWidget(self))  # This squeezes out docks.
        self.centralWidget().setLayout(QVBoxLayout())

        # pg_widget = pg.PlotWidget()
        pg_widget = pg.GraphicsLayoutWidget()
        self.centralWidget().layout().addWidget(pg_widget)

        self.cis = []
        for plot_ix in range(3):
            new_plot = pg_widget.addPlot()
            new_ci = pg.PlotCurveItem()
            new_ci.setPen(QColor(*np.random.randint(0, 255 + 1, 3).tolist()))
            new_ci.setData(y=np.zeros((NSAMPLES,)))
            # pg_widget.addItem(new_ci)
            new_plot.addItem(new_ci)
            self.cis.append(new_ci)

    def update(self):
        super(MyGUI, self).update()
        for ci_ix in range(len(self.cis)):
            ci = self.cis[ci_ix]
            x_data, y_data = ci.getData()
            y_data[:] = np.random.rand(NSAMPLES) + ci_ix
            ci.setData(y=y_data)
        if self.loop_count == 0:
            self.tr.print_diff()
        self.loop_count = (self.loop_count + 1) % 10


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = MyGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()