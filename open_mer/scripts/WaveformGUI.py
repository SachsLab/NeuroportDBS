import sys
from qtpy import QtCore, QtWidgets
from open_mer.dbsgui.waveform import WaveformGUI


def main():
    _ = QtWidgets.QApplication(sys.argv)
    aw = WaveformGUI()
    timer = QtCore.QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    try:
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtWidgets.QApplication.instance().exec_()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
