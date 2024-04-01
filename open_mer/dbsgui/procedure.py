import json
import subprocess
import sys
import typing
import time

import zmq
from zmq.utils.monitor import parse_monitor_message
from qtpy import QtCore, QtWidgets
from serf.tools.db_wrap import DBWrapper

from .widgets.ini_window import IniWindow
from .widgets.SettingsDialog import SettingsDialog
import open_mer.data_source
import open_mer.data_source.interface


class ProcedureGUI(IniWindow):

    def __init__(self):
        self._data_source: typing.Optional[open_mer.data_source.interface.IDataSource] = None
        self._source_settings = {}

        super().__init__()

        self._popen_snips: typing.Optional[subprocess.Popen] = None
        self._popen_feats: typing.Optional[subprocess.Popen] = None
        self._b_recording = False

        self._init_connection()
        self._setup_ui()

        self._subject_settings = {}
        self._procedure_settings = {}

        self.show()
        self._do_modal_settings()

    def __del__(self):
        if self._data_source is not None:
            self._data_source.set_recording_state(False, {"filename": None})
            self._data_source.disconnect_requested()
        super().__del__()
        self._term_popen()

    def parse_settings(self):
        # Handles MainWindow geometry and collects self._theme_settings and self._ipc_settings
        super().parse_settings()
        # Get custom settings
        for ini_path in self._settings_paths:
            settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

            # Store / update connection settings which will be triggered after all ini processing
            settings.beginGroup("data-source")
            for k, t in {
                "class": str,
                "basepath": str,
            }.items():
                if k in settings.allKeys():
                    if k == "class":
                        src_cls = getattr(open_mer.data_source, str(settings.value(k, type=t)))
                        self._source_settings[k] = src_cls
                        self._source_settings["settings_path"] = ini_path
                    else:
                        self._source_settings[k] = settings.value(k, type=t)
            settings.endGroup()  # data-source

    def _setup_ipc(self):
        self._sock_context = zmq.Context()

        self._feature_pub_online = False
        self._features_sock = self._sock_context.socket(zmq.SUB)
        self._feature_monitor = self._features_sock.get_monitor_socket()
        self._features_sock.connect(f"tcp://localhost:{self._ipc_settings['features']}")
        self._features_sock.setsockopt_string(zmq.SUBSCRIBE, "features")

        self._snippet_pub_online = False
        self._snippet_sock = self._sock_context.socket(zmq.SUB)
        self._snippet_monitor = self._snippet_sock.get_monitor_socket()
        self._snippet_sock.connect(f"tcp://localhost:{self._ipc_settings['snippet_status']}")
        self._snippet_sock.setsockopt_string(zmq.SUBSCRIBE, "snippet_status")

        self._procedure_sock = self._sock_context.socket(zmq.PUB)
        self._procedure_sock.bind(f"tcp://*:{self._ipc_settings['procedure_settings']}")

    def _cleanup_ipc(self):
        for _sock in [
            self._features_sock,
            self._feature_monitor,
            self._snippet_sock,
            self._snippet_monitor,
            self._procedure_sock
        ]:
            _sock.setsockopt(zmq.LINGER, 0)
            _sock.close()
        self._sock_context.term()

    @QtCore.Slot(QtCore.QObject)
    def _on_source_connected(self, data_source: open_mer.data_source.interface.IDataSource) -> None:
        self._data_source = data_source

    def _init_connection(self):
        if "class" in self._source_settings and self._source_settings["class"] is not None:
            # TODO: self._data_source ?!
            _data_source = self._source_settings["class"](
                settings_path=self._source_settings["settings_path"],
                on_connect_cb=self._on_source_connected
            )

    def _term_popen(self):
        if self._popen_snips is not None:
            self._popen_snips.terminate()
            self._popen_snips = None
        if self._popen_feats is not None:
            self._popen_feats.terminate()
            self._popen_feats = None

    def _setup_ui(self):
        self.setWindowTitle("OpenMER Procedure")
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)

        lo = QtWidgets.QHBoxLayout()

        # Settings button
        settings_pb = QtWidgets.QPushButton("Settings")
        settings_pb.setObjectName("Settings_PushButton")
        settings_pb.setMaximumWidth(50)
        settings_pb.clicked.connect(lambda state: self._do_modal_settings())
        lo.addWidget(settings_pb)

        # Record button
        lo.addSpacing(5)
        record_pb = QtWidgets.QPushButton("Record")
        record_pb.setObjectName("Record_PushButton")
        record_pb.setMaximumWidth(50)
        record_pb.clicked.connect(lambda: self.toggle_recording(None))
        lo.addWidget(record_pb)

        main_widget.setLayout(lo)

    def _publish_settings(self):
        # Sanitize some settings for serialization.
        _proc_settings = {}
        for k, v in self._procedure_settings.items():
            if hasattr(v, "isoformat"):
                _proc_settings[k] = v.isoformat()
            elif hasattr(v, "tolist"):
                _proc_settings[k] = v.tolist()
            else:
                _proc_settings[k] = v

        send_dict = {
            "procedure": _proc_settings,
            "subject": {**self._subject_settings, "birthday": self._subject_settings["birthday"].isoformat()},
            "recording": {"state": self._b_recording}
        }
        pub_string = "procedure_settings " + json.dumps(send_dict)
        print(f"Publishing: {pub_string}")
        self._procedure_sock.send_string(pub_string)

    def _do_modal_settings(self) -> bool:
        win = SettingsDialog(self._subject_settings, self._procedure_settings)
        result = win.exec_()
        if result == QtWidgets.QDialog.Accepted:
            # Update self._subject_settings and self._procedure_settings from values in the dialog
            win.update_settings()

            # Load or create subject
            # Returns subject_id/-1 whether subject is properly created or not
            sub_id = DBWrapper().load_or_create_subject(self._subject_settings)

            if sub_id == -1:
                print("Subject not created.")
                return False
            else:
                # Update settings with the true subject and procedure ids from the database
                self._subject_settings["subject_id"] = sub_id
                self._procedure_settings["subject_id"] = sub_id
                proc_id = DBWrapper().load_or_create_procedure(self._procedure_settings)
                self._procedure_settings["procedure_id"] = proc_id

            self._publish_settings()
            return True
        else:
            return False

    def toggle_recording(self, on_off: typing.Optional[bool] = None):
        if self._data_source is None:
            return

        on_off = on_off if on_off is not None else not self._b_recording
        if on_off:
            if self._b_recording:
                # Wants on but already recording. Stop then start again.
                self.toggle_recording(False)
                time.sleep(0.100)
            self._b_recording = True
            self._publish_settings()  # re-send the settings
        else:
            self._b_recording = False
        self._run_recording(self._b_recording)

        record_pb: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "Record_PushButton")
        rec_facecolor = "red" if self._b_recording else "gray"
        record_pb.setStyleSheet("QPushButton { color: white; "
                                f"background-color : {rec_facecolor}; "
                                f"border-color : {rec_facecolor}; "
                                "border-width: 2px}")

    def _check_monitors(self):
        for proc in ["snippet", "feature"]:
            _monitor = getattr(self, f"_{proc}_monitor")
            monitor_result = _monitor.poll(10, zmq.POLLIN)
            if monitor_result:
                data = _monitor.recv_multipart()
                evt = parse_monitor_message(data)
                if evt["event"] in (
                        zmq.EVENT_ACCEPTED,
                        zmq.EVENT_CONNECTED,
                        zmq.EVENT_HANDSHAKE_SUCCEEDED
                ):
                    setattr(self, f"_{proc}_pub_online", True)
                elif evt["event"] in (
                        zmq.EVENT_DISCONNECTED,
                        zmq.EVENT_MONITOR_STOPPED,
                        zmq.EVENT_CLOSED,
                ):
                    setattr(self, f"_{proc}_pub_online", False)
                elif evt["event"] in (
                    zmq.EVENT_CONNECT_DELAYED,
                    zmq.EVENT_CONNECT_RETRIED
                ):
                    pass
                else:
                    print(f"TODO: handle {evt['event']}")

    def _run_recording(self, on_off: bool):
        # Manage Snippets_Process
        self._term_popen()
        self._check_monitors()
        if self._popen_snips is None and not self._snippet_pub_online and on_off:
            self._popen_snips = subprocess.Popen([
                sys.executable,
                "-m",
                "open_mer.scripts.Snippets_Process",
                f"--procedure-id={self._procedure_settings['procedure_id']}"
            ])
        if self._popen_feats is None and not self._feature_pub_online and on_off:
            self._popen_feats = subprocess.Popen([
                sys.executable,
                "-m",
                "open_mer.scripts.Features_Process",
                f"--procedure-id={self._procedure_settings['procedure_id']}"
            ])

        f_name, m_name, l_name = self.parse_patient_name(self._subject_settings['name'])
        file_info = {'filename': self._get_filename(),
                     'comment': self._subject_settings['NSP_comment'],
                     'patient_info': {'ID': self._subject_settings['id'],
                                      # if only single name, returned in l_name
                                      'firstname': f_name if f_name else l_name,
                                      'middlename': m_name,  # TODO: implement MiddleName
                                      'lastname': l_name,
                                      'DOBMonth': self._subject_settings['birthday'].month,
                                      'DOBDay': self._subject_settings['birthday'].day,
                                      'DOBYear': self._subject_settings['birthday'].year
                                      }}
        return self._data_source.set_recording_state(on_off, file_info)

    @staticmethod
    def parse_patient_name(full_name):
        # parse the subject information
        names = full_name.split(' ')
        m_name = ''
        m_idx = -1
        l_idx = -1
        for idx, n in enumerate(names):
            if all([x.isupper() for x in n]):
                m_idx = idx
                l_idx = idx + 1
                m_name = n
                break

        f_name = str.join(' ', names[:m_idx])
        l_name = str.join(' ', names[l_idx:])
        return f_name, m_name, l_name

    def _get_filename(self):
        import os
        return os.path.normpath(os.path.join(
            self._source_settings["basepath"],
            self._subject_settings["id"],
            "_".join([
                self._procedure_settings["date"].strftime('%m%d%y'),
                self._subject_settings["id"],
                self._procedure_settings["target_name"],
                self._procedure_settings["recording_config"]
            ])
        ))

    def update(self):
        b_publish_settings = False

        # Fetch any new features
        try:
            received_msg = self._features_sock.recv_string(flags=zmq.NOBLOCK)[len("features") + 1:]
            b_publish_settings |= received_msg == "refresh"
        except zmq.ZMQError:
            pass

        self._check_monitors()
        try:
            received_msg = self._snippet_sock.recv_string(flags=zmq.NOBLOCK)[len("snippet_status") + 1:]
            b_publish_settings |= received_msg == "refresh"
        except zmq.ZMQError:
            pass

        # Fetch the status of the snippet process
        if b_publish_settings:
            self._publish_settings()
