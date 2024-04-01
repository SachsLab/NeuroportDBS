from qtpy import QtWidgets

from open_mer.dbsgui.comments import CommentsGUI


def main():
    import sys
    qapp = QtWidgets.QApplication(sys.argv)
    window = CommentsGUI()
    window.show()
    sys.exit(qapp.exec_())


if __name__ == '__main__':
    main()
