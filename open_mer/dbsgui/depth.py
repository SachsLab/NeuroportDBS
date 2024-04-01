from qtpy import QtCore, QtWidgets
import zmq
from .widgets.ini_window import IniWindow
from ..depth_source import CBSDKPlayback
try:
    from cerebuswrapper import CbSdkConnection
except ModuleNotFoundError as e:
    print(e, "Try `pip install git+https://github.com/SachsLab/cerebuswrapper.git`.")

import open_mer.depth_source


class MyLCD(QtWidgets.QLCDNumber):
    lcd_dbl_clicked = QtCore.Signal()

    def mouseDoubleClickEvent(self, event):
        # event is a PySide6.QtGui.QMouseEvent
        self.lcd_dbl_clicked.emit()


class DepthGUI(IniWindow):

    def __init__(self):
        self._depth_sock = None
        self._data_settings = {"source": {"class": None, "serial": {}}, "mirror": {"lsl": None, "nsp": None}}
        self._depth_source = None
        super().__init__()
        self.display_string = None
        self._depth_stream = None
        self._init_connection()
        self.setup_ui()

    def parse_settings(self):
        # Handles MainWindow geometry and collects self._theme_settings and self._ipc_settings
        super().parse_settings()
        # Get custom settings
        for ini_path in self._settings_paths:
            settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

            settings.beginGroup("depth-source")
            for k, t in {
                "class": str,
            }.items():
                if k in settings.allKeys():
                    if k == "class":
                        src_cls = getattr(open_mer.depth_source, settings.value(k, type=t))
                        self._data_settings["source"][k] = src_cls
                    else:
                        self._data_settings["source"][k] = settings.value(k, type=t)
            settings.beginGroup("serial")
            for k, t in {
                "baudrate": int, "com_port": str
            }.items():
                if k in settings.allKeys():
                    self._data_settings["source"]["serial"][k] = settings.value(k, type=t)
            settings.endGroup()  # serial
            settings.endGroup()  # depth-source

            settings.beginGroup("depth-mirror")
            for k, t in {
                "lsl_mirror": bool, "nsp_mirror": bool
            }.items():
                if k in settings.allKeys():
                    self._data_settings["mirror"][k] = settings.value(k, type=t)
            settings.endGroup()  # depth-mirror

    def _setup_ipc(self):
        self._depth_context = zmq.Context()
        self._depth_sock = self._depth_context.socket(zmq.PUB)
        self._depth_sock.bind(f"tcp://*:{self._ipc_settings['ddu']}")

        if self._data_settings["mirror"]["lsl"]:
            import pylsl
            outlet_info = pylsl.StreamInfo(name='electrode_depth', type='depth', channel_count=1,
                                           nominal_srate=pylsl.IRREGULAR_RATE, channel_format=pylsl.cf_float32,
                                           source_id='depth1214')
            self._depth_stream = pylsl.StreamOutlet(outlet_info)

        src_cls = self._data_settings["source"]["class"]
        if src_cls is not None and src_cls != open_mer.depth_source.CBSDKPlayback:
            # We have a data source that is not CBSDKPlayback (e.g., serial, or some other)
            #  so we want to send the NSP comments about our depths so they get saved in the .nev file.
            CbSdkConnection().connect()
            CbSdkConnection().cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}
            # cbsdk_conn.set_comments("DTT:" + display_string)

    def _cleanup_ipc(self):
        self._depth_sock.setsockopt(zmq.LINGER, 0)
        self._depth_sock.close()
        self._depth_context.term()

        if self._depth_stream is not None:
            del self._depth_stream
            self._depth_stream = None

        src_cls = self._data_settings["source"]["class"]
        if src_cls is not None and src_cls != open_mer.depth_source.CBSDKPlayback:
            CbSdkConnection().disconnect()

    def _init_connection(self):
        if self._data_settings["source"]["class"] is not None:
            self._depth_source = self._data_settings["source"]["class"]()

    def __del__(self):
        if self._depth_source is not None:
            self._depth_source.do_close()
            self._depth_source = None
        super().__del__()

    def setup_ui(self):
        self.setWindowTitle("DDU")
        self.show()
        self.plot_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.plot_widget)

        # define Qt GUI elements
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setSpacing(0)
        v_layout.setContentsMargins(10, 0, 10, 10)

        h_layout = QtWidgets.QHBoxLayout()

        h_layout.addWidget(QtWidgets.QLabel("DTT: "))
        dtt_spinbox = QtWidgets.QDoubleSpinBox()
        dtt_spinbox.setObjectName("DTT_doubleSpinBox")
        dtt_spinbox.setMinimum(-100.00)
        dtt_spinbox.setMaximum(100.00)
        dtt_spinbox.setSingleStep(1.00)
        dtt_spinbox.setDecimals(2)
        dtt_spinbox.setValue(0.00)
        dtt_spinbox.setFixedWidth(80)
        h_layout.addWidget(dtt_spinbox)
        
        # Manual offset added to the depth before display and mirroring
        h_layout.addWidget(QtWidgets.QLabel("Offset: "))
        offset_spinbox = QtWidgets.QDoubleSpinBox()
        offset_spinbox.setObjectName("offset_doubleSpinBox")
        offset_spinbox.setMinimum(-100.00)
        offset_spinbox.setMaximum(100.00)
        offset_spinbox.setSingleStep(1.00)
        offset_spinbox.setDecimals(2)
        offset_spinbox.setValue(self._depth_source.offset)
        offset_spinbox.setFixedWidth(80)
        h_layout.addWidget(offset_spinbox)

        h_layout.addStretch()
        v_layout.addLayout(h_layout)

        # add a frame for the LCD numbers
        lcd_frame = QtWidgets.QFrame()
        lcd_frame.setFrameShape(QtWidgets.QFrame.Shape.Box)
        lcd_layout = QtWidgets.QGridLayout()
        lcd_frame.setLayout(lcd_layout)

        # RAW reading from DDU
        raw_ddu_lcd = QtWidgets.QLCDNumber()
        raw_ddu_lcd.setObjectName("raw_ddu_LCD")
        raw_ddu_lcd.setDigitCount(7)
        raw_ddu_lcd.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        raw_ddu_lcd.setSmallDecimalPoint(True)
        raw_ddu_lcd.setFixedHeight(50)
        raw_ddu_lcd.display("{0:.3f}".format(0))
        lcd_layout.addWidget(raw_ddu_lcd, 0, 3, 2, 3)

        offset_lcd = MyLCD()
        offset_lcd.setObjectName("offset_LCD")
        offset_lcd.setDigitCount(7)
        offset_lcd.setFixedHeight(150)
        offset_lcd.display("{0:.3f}".format(-10))
        offset_lcd.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        offset_lcd.lcd_dbl_clicked.connect(self.publish)
        lcd_layout.addWidget(offset_lcd, 2, 0, 5, 6)

        v_layout.addWidget(lcd_frame)

        self.plot_widget.setLayout(v_layout)

    def update(self):
        value = self._depth_source.update()
        if value is not None:
            # Find widgets
            raw_ddu_lcd: QtWidgets.QLCDNumber = self.findChild(QtWidgets.QLCDNumber, "raw_ddu_LCD")
            offset_lcd: MyLCD = self.findChild(MyLCD, "offset_LCD")
            dtt_spinbox: QtWidgets.QDoubleSpinBox = self.findChild(QtWidgets.QDoubleSpinBox, "DTT_doubleSpinBox")
            offset_spinbox: QtWidgets.QDoubleSpinBox = self.findChild(QtWidgets.QDoubleSpinBox, "offset_doubleSpinBox")

            # Update displays for raw and corrected values
            raw_ddu_lcd.display("{0:.3f}".format(value))
            value += dtt_spinbox.value() + offset_spinbox.value()
            display_string = "{0:.3f}".format(value)
            offset_lcd.display(display_string)

            # If value is new, store and publish
            if display_string != self.display_string:
                self.display_string = display_string
                self.publish()

    def publish(self):
        # Push to NSP (only if this is not NSP playback)
        src_cls = self._data_settings["source"]["class"]
        if src_cls is not None and src_cls != open_mer.depth_source.CBSDKPlayback:
            cbsdk_conn = CbSdkConnection()
            if not cbsdk_conn.is_connected:
                cbsdk_conn.connect()
                cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}
            if cbsdk_conn.is_connected:
                cbsdk_conn.set_comments("DTT:" + self.display_string)

        # Push to LSL
        if self._depth_stream is not None:
            self._depth_stream.push_sample([self.display_string])

        # Publish on ZeroMQ
        self._depth_sock.send_string(f"ddu {self.display_string}")
