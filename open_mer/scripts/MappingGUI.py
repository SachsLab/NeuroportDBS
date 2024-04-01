import sys
import qtpy
from qtpy import QtWidgets, QtCore
from open_mer.dbsgui.mapping import MappingGUI


def main():
    _ = QtWidgets.QApplication(sys.argv)
    aw = MappingGUI()
    # timer = QTimer()
    # timer.timeout.connect(aw.update)
    # timer.start(1000)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()


if __name__ == '__main__':
    main()
