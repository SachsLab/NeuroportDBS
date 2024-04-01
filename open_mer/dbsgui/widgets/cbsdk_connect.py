import os
import sys
from qtpy import uic
from qtpy import QtWidgets


ui_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ui')
Ui_mydialog, ui_mybassclass = uic.loadUiType(os.path.join(ui_path, 'cbsdk_connect.ui'))


class ConnectDialog(QtWidgets.QDialog, Ui_mydialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        Ui_mydialog.__init__(self)
        self.setupUi(self)
        if sys.platform != 'win32':
            self.spinBox_recv_buff.setValue(6 * 1024 * 1024)

    def do_connect(self):
        from cerebuswrapper import CbSdkConnection
        con_params = {
            'client-addr': self.lineEdit_client_ip.text(),
            'client-port': self.spinBox_client_port.value(),
            'inst-addr': self.lineEdit_inst_addr.text(),
            'inst-port': self.spinBox_inst_port.value(),
            'receive-buffer-size': self.spinBox_recv_buff.value()
        }
        cbsdkConn = CbSdkConnection(con_params=con_params)  # Instance, so no need to return it.
        return cbsdkConn.connect()
