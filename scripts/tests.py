from qtpy.QtWidgets import QMainWindow, QPushButton
from qtpy.QtCore import Qt
import sys
import time


class TestQProgressBar(QMainWindow):
    def __init__(self):
        super(TestQProgressBar, self).__init__()
        bar = QPushButton("TEST")
        # bar.setFlat(True)
        bar.setStyleSheet('QPushButton {background: red; background-color: blue;}')
        self.layout().addWidget(bar)


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication

    qapp = QApplication(sys.argv)
    pb = TestQProgressBar()
    pb.show()

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
