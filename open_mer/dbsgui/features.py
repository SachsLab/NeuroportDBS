import json
import importlib.resources as pkg_resources

import zmq
from qtpy import QtCore, QtWidgets, QtGui
from serf.tools.db_wrap import DBWrapper

from ..feature_plots import *
from .widgets.custom import CustomWidget, CustomGUI


class FeatureStackWidget(CustomWidget):

    def __init__(self, *args, theme={}, plot={}, features={}, procedure={}):
        with pkg_resources.path(f"{__package__.split('.')[0]}.resources", "icons") as res_icons_path:
            res_icons_path = res_icons_path
        self.status_icons = {
            k: QtGui.QPixmap(str(res_icons_path / (v + '.png')))
            for k, v in {
                "accumulating": "depth_status_delay",
                "recording": "depth_status_in_use",
                "done": "depth_status_done",
                "notrecording": "depth_status_off"
            }.items()
        }
        self._plot_config = {}
        self._features = {}
        # self._theme = {} created by super
        super().__init__(*args, theme=theme, plot=plot, features=features, procedure=procedure)
        self.reset_feat_select_items()
        self.reset_chan_select_items()

    def _parse_config(self, theme={}, plot={}, features={}, procedure={}):
        super()._parse_config(theme=theme)
        filter = plot.get("filter", {})
        self._plot_config = plot["plot"].copy()
        self._plot_config["highpass"] = filter.get("highpass", True)
        # This next 2 lines convert our dict from {ind: {name: enabled}} to {ind: name)} only for enabled
        self._features = {k: [(_k, _v) for _k, _v in v.items()][0] for k, v in features.items()}
        self._features = {k: v[0] for k, v in self._features.items() if v[1]}
        self._procedure = procedure.copy()

    def create_control_panel(self):
        # | chan_select | feature_select     |                      |               |
        # |----------------------------------|      status icon     |   refresh     |
        # | y-range | highpass | match sweep |                      |               |

        lo_L1 = QtWidgets.QHBoxLayout()

        # Channel select
        lo_L1.addWidget(QtWidgets.QLabel("Electrode: ", alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))
        chan_select_cb = QtWidgets.QComboBox()
        chan_select_cb.setObjectName("ChanSelect_ComboBox")
        chan_select_cb.setMinimumWidth(70)
        chan_select_cb.setEnabled(False)
        chan_select_cb.addItem("None")
        chan_select_cb.currentIndexChanged.connect(self.refresh_axes)
        lo_L1.addWidget(chan_select_cb)

        # Feature select
        lo_L1.addSpacing(20)
        lo_L1.addWidget(QtWidgets.QLabel("Feature set: ", alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))
        feat_select_cb = QtWidgets.QComboBox()
        feat_select_cb.setObjectName("FeatureSelect_ComboBox")
        feat_select_cb.setMinimumWidth(60)
        feat_select_cb.currentIndexChanged.connect(self.refresh_axes)
        lo_L1.addWidget(feat_select_cb)

        # Second row - left: y-range, highpass, match sweep; right: refresh
        lo_L2 = QtWidgets.QHBoxLayout()
        lo_L2.addSpacing(10)

        # Range Edit
        lo_L2.addWidget(QtWidgets.QLabel("+/- ", alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))
        range_edit = QtWidgets.QLineEdit("{:.2f}".format(self._plot_config['y_range']))
        range_edit.setObjectName("Range_LineEdit")
        range_edit.setMaximumWidth(50)
        range_edit.editingFinished.connect(self.on_range_edited)
        lo_L2.addWidget(range_edit)

        # HP
        lo_L2.addSpacing(30)
        hp_chk = QtWidgets.QCheckBox("HP")
        hp_chk.setObjectName("HP_CheckBox")
        hp_chk.setChecked(self._plot_config["highpass"])
        lo_L2.addWidget(hp_chk)

        # Match Sweep
        lo_L2.addSpacing(30)
        sweep_chk = QtWidgets.QCheckBox("Match SweepGUI")
        sweep_chk.setObjectName("Sweep_CheckBox")
        sweep_chk.setChecked(True)
        sweep_chk.setEnabled(True)
        sweep_chk.clicked.connect(self.on_sweep_clicked)
        lo_L2.addWidget(sweep_chk)

        lo_R = QtWidgets.QHBoxLayout()

        # Status Label
        status_label = QtWidgets.QLabel()
        status_label.setObjectName("Status_Label")
        status_label.setPixmap(self.status_icons["notrecording"])
        lo_R.addWidget(status_label)
        lo_R.addSpacing(10)

        # Refresh button
        refresh_pb = QtWidgets.QPushButton("Refresh")
        refresh_pb.setObjectName("Refresh_PushButton")
        refresh_pb.setMaximumWidth(50)
        lo_R.addWidget(refresh_pb)

        # Combine layouts
        lo_L = QtWidgets.QVBoxLayout()
        lo_L.addLayout(lo_L1)
        lo_L.addSpacing(5)
        lo_L.addLayout(lo_L2)

        lo = QtWidgets.QHBoxLayout()
        lo.addLayout(lo_L)
        lo.addStretch()
        lo.addLayout(lo_R)
        self.layout().addLayout(lo)

    def on_range_edited(self):
        range_edit = self.findChild(QtWidgets.QLineEdit, "Range_LineEdit")
        self._plot_config["y_range"] = float(range_edit.text())

    def on_sweep_clicked(self):
        sweep_control: QtWidgets.QCheckBox = self.findChild(QtWidgets.QCheckBox, "Sweep_CheckBox")
        chan_combo: QtWidgets.QComboBox = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        hp_chk: QtWidgets.QCheckBox = self.findChild(QtWidgets.QCheckBox, "HP_CheckBox")
        range_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "Range_LineEdit")
        b_enable = not sweep_control.isChecked()
        for _ in [chan_combo, hp_chk, range_edit]:
            _.setEnabled(b_enable)

    def create_plots(self):
        plot_stack = self.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        if plot_stack is None:
            plot_stack = QtWidgets.QStackedWidget()
            plot_stack.setObjectName("Plot_Stack")
            self.layout().addWidget(plot_stack)

        # Clear old widgets from the stack
        to_delete = [plot_stack.widget(_) for _ in range(plot_stack.count())]
        for wid in to_delete:
            plot_stack.removeWidget(wid)
            wid.deleteLater()

        self._widget_stack = {}  # dict of dicts. Outer key is channel label. Inner key is feature label.
        plot_class_map = {
            'Raw': RawPlots, 'Mapping': MappingPlots, 'STN': STNPlots, 'LFP': LFPPlots, 'Spikes': SpikePlots,
            None: NullPlotWidget
        }

        n_feats = len(self._features)
        chan_labels = self._procedure.get("chan_labels", []) + ["None"]
        self._theme["color_iterator"] = -1
        for chan_ix, chan_label in enumerate(chan_labels):
            self._theme["color_iterator"] = (self._theme["color_iterator"] + 1) % len(self._theme["pencolors"])
            pcolor = self._theme["pencolors"][self._theme["color_iterator"]]
            self._widget_stack[chan_label] = {}
            for feat_ix, f in self._features.items():
                self._widget_stack[chan_label][f] = [n_feats * chan_ix + feat_ix, 0]
                w_cls = plot_class_map[f] if f in plot_class_map else NullPlotWidget
                plot_stack.addWidget(w_cls({**self._plot_config, "pen_color": pcolor}))
        plot_stack.setCurrentIndex(0)

    def refresh_axes(self, ix: int = 0):
        # We ignore ix from single-widget interaction events.
        # We instead retrieve the key from a combination of widgets.
        plot_stack: QtWidgets.QStackedWidget = self.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        chan_combo: QtWidgets.QComboBox = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        feat_combo: QtWidgets.QComboBox = self.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        chan_key = chan_combo.currentText()
        feat_key = feat_combo.currentText()
        if chan_key and feat_key:
            idx = self._widget_stack[chan_key][feat_key][0]
            plot_stack.setCurrentIndex(idx)

    def clear(self):
        pass

    def reset_feat_select_items(self):
        feat_combo: QtWidgets.QComboBox = self.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        feat_combo.blockSignals(True)
        feat_combo.clear()
        feat_combo.addItems(list(self._features.values()))
        feat_combo.blockSignals(False)
        feat_combo.setCurrentIndex(0)

    def reset_chan_select_items(self):
        chan_labels = self._procedure.get("chan_labels", []) + ["None"]
        chan_combo: QtWidgets.QComboBox = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        chan_combo.blockSignals(True)
        chan_combo.clear()
        chan_combo.addItems(chan_labels)
        chan_combo.blockSignals(False)
        chan_combo.setCurrentIndex(0)  # Triggers an emission --> refresh_axes

    def handle_ipc_channel_select(self, chan_settings: dict):
        sweep_control: QtWidgets.QCheckBox = self.findChild(QtWidgets.QCheckBox, "Sweep_CheckBox")
        if sweep_control.isChecked():
            chan_combo: QtWidgets.QComboBox = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
            avail_chans = [chan_combo.itemText(_) for _ in range(chan_combo.count())]
            if chan_settings["label"] in avail_chans:
                chan_combo.setCurrentIndex(avail_chans.index(chan_settings["label"]))


class FeaturesGUI(CustomGUI):
    widget_cls = FeatureStackWidget

    def __init__(self):
        """
        - Visualizes raw segments and calculated features from the database
        - Widgets to navigate the visualizations
        - Subscribes to zmq messages to know which features to grab
        - Subscribes to zmq messages to know which channels to show
        - For semi-realtime application, you should be running Depth_Process and Features_Process (from serf package)
          in background.
        """
        self._plot_settings = {}
        self._subject_settings = {}
        self._procedure_settings = {}
        self._features_settings = {}
        self._chan_labels = []
        self._plot_widget: FeatureStackWidget | None = None  # This will get updated in super init but it helps type hints
        self._db = DBWrapper()
        super().__init__()
        # Try to get the current procedure.
        self._features_sock.send_string("features refresh")

    def parse_settings(self):
        super().parse_settings()

        if "plot" not in self._plot_settings:
            self._plot_settings["plot"] = {}

        if "filter" not in self._plot_settings:
            self._plot_settings["filter"] = {}

        for ini_path in self._settings_paths:
            settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

            settings.beginGroup("plot")
            for k, t in {"x_start": int, "x_stop": int, "y_range": int, "image_plot": bool}.items():
                if k in settings.allKeys():
                    self._plot_settings["plot"][k] = settings.value(k, type=t)
            settings.endGroup()

            settings.beginGroup("buffer")
            if "highpass" in settings.allKeys():
                self._plot_settings["filter"]["highpass"] = settings.value("highpass", type=bool)
            settings.endGroup()

            settings.beginGroup("features")
            feat_inds = [int(_) for _ in settings.childGroups()]
            feat_inds.sort()
            for f_ind in feat_inds:
                settings.beginGroup(str(f_ind))
                self._features_settings[f_ind] = {settings.value("name", type=str): settings.value("enable", type=bool)}
                settings.endGroup()
            settings.endGroup()  # features

            settings.beginGroup("theme")
            for k in settings.allKeys():
                self._theme_settings[k] = settings.value(k, type=str)
            settings.endGroup()  # status

    def _setup_ipc(self):
        self._zmq_context = zmq.Context()

        # Subscribe to channel-change notifications -- so we can update which channel we are viewing
        self._chan_sock = self._zmq_context.socket(zmq.SUB)
        self._chan_sock.connect(f"tcp://localhost:{self._ipc_settings['channel_select']}")
        self._chan_sock.setsockopt_string(zmq.SUBSCRIBE, "channel_select")

        # Subscribe to procedure set notifications -- load data
        self._procedure_sock = self._zmq_context.socket(zmq.SUB)
        self._procedure_sock.connect(f"tcp://localhost:{self._ipc_settings['procedure_settings']}")
        self._procedure_sock.setsockopt_string(zmq.SUBSCRIBE, "procedure_settings")

        # Subscribe to snippet status -- update icon and trigger plot update
        self._snippet_sock = self._zmq_context.socket(zmq.SUB)
        self._snippet_sock.connect(f"tcp://localhost:{self._ipc_settings['snippet_status']}")
        self._snippet_sock.setsockopt_string(zmq.SUBSCRIBE, "snippet_status")

        # Publish refresh notification -- on startup and when refresh is clicked
        self._features_sock = self._zmq_context.socket(zmq.PUB)
        self._features_sock.bind(f"tcp://*:{self._ipc_settings['features']}")

    def _cleanup_ipc(self):
        for _sock in [self._chan_sock, self._procedure_sock, self._snippet_sock, self._features_sock]:
            _sock.setsockopt(zmq.LINGER, 0)
            _sock.close()
        self._zmq_context.term()

    def try_reset_widget(self):
        # Do not call super().try_reset_widget(), because it expects a data source and here we don't care
        #  if cerebus is running
        self.on_plot_closed(force=True)
        source_dict = {
            "channel_names": self._chan_labels,
            "chan_states": None,
            "srate": None
        }
        # srate = int(SAMPLINGGROUPS[self._group_ix])
        #         extra = {}
        #
        #         # self._chan_states = pd.DataFrame(columns=['name', 'src', 'unit', 'type', 'pos'])
        #         for ch_ix, ch_dict in enumerate(self._group_info):
        #             chan_names.append(ch_dict['label'])
        #             ch_info = self._cbsdk_conn.get_channel_info(ch_dict['chan'])
        #             chan_states.append({
        #                 'name': ch_dict['label'],
        #                 'src': ch_dict['chan'],
        #                 'unit': ch_dict['unit'],
        #                 'gain': ch_dict['gain'],
        #                 'spkthrlevel': ch_info['spkthrlevel']
        #             })
        self._plot_widget = self.__class__.widget_cls(
            source_dict,
            theme=self._theme_settings,
            plot=self._plot_settings,
            features=self._features_settings,
            procedure={**self._procedure_settings, "chan_labels": self._chan_labels}
        )
        self._plot_widget.was_closed.connect(self.on_plot_closed)
        self.setCentralWidget(self._plot_widget)

        # After creating _plot_widget, update its widgets
        refresh_pb: QtWidgets.QPushButton = self._plot_widget.findChild(QtWidgets.QPushButton, "Refresh_PushButton")
        refresh_pb.clicked.connect(self.on_refresh_clicked)

    def manage_refresh(self):
        plot_stack: QtWidgets.QStackedWidget = self._plot_widget.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        chan_combo: QtWidgets.QComboBox = self._plot_widget.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        feat_combo: QtWidgets.QComboBox = self._plot_widget.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        stack_item = self._widget_stack[chan_combo.currentText()][feat_combo.currentText()]
        plot_stack.widget(stack_item[0]).clear_plot()
        stack_item[1] = 0

    def on_refresh_clicked(self):
        self._features_sock.send_string("features refresh")

    def _check_ipc(self):
        try:
            received_msg = self._chan_sock.recv_string(flags=zmq.NOBLOCK)[len("channel_select") + 1:]
            chan_settings = json.loads(received_msg)
            # ^ dict with k,v_type "channel":int, "range":[float, float], "highpass":bool
            self._plot_widget.handle_ipc_channel_select(chan_settings)
        except zmq.ZMQError:
            pass

        try:
            received_msg = self._procedure_sock.recv_string(flags=zmq.NOBLOCK)[len("procedure_settings") + 1:]
            procedure_settings = json.loads(received_msg)
            # ^ dict with settings for "procedure", "subject"
            if "procedure" in procedure_settings and "procedure_id" in procedure_settings["procedure"]:
                procedure_id = procedure_settings["procedure"]["procedure_id"]
                if procedure_id != self._db.current_procedure or len(self._chan_labels) == 0:
                    self._db.select_procedure(procedure_id)
                    self._chan_labels = self._db.list_channel_labels()
                    print(f"Resetting features for procedure {procedure_id} with channels {self._chan_labels}")
                    self.try_reset_widget()
        except zmq.ZMQError:
            pass

        try:
            received_msg = self._snippet_sock.recv_string(flags=zmq.NOBLOCK)[len("snippet_status") + 1:]

            # Depth processor has (re)started. Maybe trigger a refresh?
            # received_msg == "startup"

            # Update the status.
            status_label = self._plot_widget.findChild(QtWidgets.QLabel, "Status_Label")
            if received_msg in self._plot_widget.status_icons:
                status_label.setPixmap(self._plot_widget.status_icons[received_msg])
        except zmq.ZMQError:
            pass

    def do_plot_update(self):
        self._check_ipc()

        # TODO: Maintain state of current channel label, current feature, last_id, do_hp

        plot_stack: QtWidgets.QStackedWidget = self._plot_widget.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        chan_combo: QtWidgets.QComboBox = self._plot_widget.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        feat_combo: QtWidgets.QComboBox = self._plot_widget.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        sweep_cb: QtWidgets.QCheckBox = self._plot_widget.findChild(QtWidgets.QCheckBox, "Sweep_CheckBox")

        curr_widget = plot_stack.currentWidget()
        curr_chan_lbl = chan_combo.currentText() if chan_combo.count() > 0 else "None"
        b_sweep_sync = sweep_cb.isChecked()

        if curr_chan_lbl != 'None':
            curr_feat = feat_combo.currentText()
            stack_item = self._plot_widget._widget_stack[curr_chan_lbl][curr_feat]
            do_hp = self._plot_settings["filter"]["highpass"]
            y_range = self._plot_settings["plot"]["y_range"]

            # If widget values don't match stored values
            if y_range != curr_widget.plot_config['y_range']\
                or do_hp != curr_widget.plot_config['highpass']:
                # Clear plots and update widgets with stored settings
                curr_widget.clear_plot()
                stack_item[1] = 0
                curr_widget.plot_config['highpass'] = do_hp
                curr_widget.plot_config['y_range'] = y_range

            curr_datum = stack_item[1]
            if curr_feat == 'Raw':
                all_data = self._db.load_depth_data(chan_lbl=curr_chan_lbl,
                                                    gt=curr_datum,
                                                    do_hp=do_hp,
                                                    return_uV=True)
            elif False and curr_feat == 'Mapping':
                # Currently not working
                all_data = self._db.load_mapping_response(chan_lbl=curr_chan_lbl,
                                                          gt=curr_datum)
            else:
                all_data = self._db.load_features_data(category=curr_feat,
                                                       chan_lbl=curr_chan_lbl,
                                                       gt=curr_datum)
            if all_data:
                plot_stack.currentWidget().update_plot(dict(all_data))
                stack_item[1] = max(all_data.keys())
