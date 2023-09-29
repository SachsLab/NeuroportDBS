import sys
from qtpy import QtCore, QtWidgets
from open_mer.dbsgui.features import FeaturesGUI


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = FeaturesGUI()
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        sys.exit(app.exec_())


if __name__ == '__main__':
    main()
