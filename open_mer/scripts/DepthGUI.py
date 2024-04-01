import sys
from qtpy import QtCore, QtWidgets
from open_mer.dbsgui.depth import DepthGUI


def main():
    _ = QtWidgets.QApplication(sys.argv)
    window = DepthGUI()
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()


if __name__ == '__main__':
    main()
