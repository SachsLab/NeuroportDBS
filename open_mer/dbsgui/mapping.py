import os
import json
from qtpy import QtWidgets, QtGui
import pylsl
from .widgets.custom import CustomGUI, CustomWidget
from ..settings.defaults import MAPPINGSTIMULI


class MappingWidget(CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # configure lsl stream for outputting markers
        outlet_info = pylsl.StreamInfo(name='sensorimotor_mapping', type='map', channel_count=1,
                                       nominal_srate=pylsl.IRREGULAR_RATE, channel_format=pylsl.cf_string,
                                       source_id='mapping1214')
        self.map_stream = pylsl.StreamOutlet(outlet_info)

    def create_control_panel(self):
        pass

    def create_plots(self, theme='dark', **kwargs):
        bold_font = QtGui.QFont()
        bold_font.setPixelSize(12)
        bold_font.setBold(True)

        self.layout().addStretch()
        self.layout().addWidget(QtWidgets.QLabel("Channels: ", font=bold_font))
        self.layout().addSpacing(10)
        # Add check boxes for channels
        self.channels = {}
        for chan_state in self.chan_states:
            chan_lbl = chan_state['name']
            chk_box = QtWidgets.QCheckBox(chan_lbl)
            chk_box.stateChanged.connect(self.check_channel_and_stim)
            self.channels[chan_lbl] = chk_box
            self.layout().addWidget(chk_box)
        self.layout().addSpacing(10)
        bt_clear = QtWidgets.QPushButton("Uncheck all")
        bt_clear.clicked.connect(lambda: self.uncheck_all(self.channels))
        self.layout().addWidget(bt_clear)
        self.layout().addSpacing(20)

        # Stimuli types
        self.layout().addWidget(QtWidgets.QLabel("Stimuli: ", font=bold_font))
        self.layout().addSpacing(10)
        self.mapping_stimuli = {}

        for stim in MAPPINGSTIMULI:
            self.mapping_stimuli[stim] = QtWidgets.QCheckBox(stim)
            self.mapping_stimuli[stim].stateChanged.connect(self.check_channel_and_stim)
            self.layout().addWidget(self.mapping_stimuli[stim])
        self.mapping_stimuli['Custom'] = QtWidgets.QCheckBox()
        l = QtWidgets.QHBoxLayout()
        self.custom_stimulus = QtWidgets.QLineEdit("Custom")
        l.addWidget(self.mapping_stimuli['Custom'])
        l.addSpacing(3)
        l.addWidget(self.custom_stimulus)
        self.layout().addLayout(l)
        self.layout().addSpacing(10)
        bt_clear = QtWidgets.QPushButton("Uncheck all")
        bt_clear.clicked.connect(lambda: self.uncheck_all(self.mapping_stimuli))
        self.layout().addWidget(bt_clear)
        self.layout().addSpacing(20)

        # side
        self.layout().addWidget(QtWidgets.QLabel("Body Side: ", font=bold_font))
        self.layout().addSpacing(10)
        self.sides = {
            'Left': QtWidgets.QCheckBox("Left"),
            'Right': QtWidgets.QCheckBox("Right")
        }
        l = QtWidgets.QHBoxLayout()
        l.addWidget(self.sides['Left'])
        l.addWidget(self.sides['Right'])
        self.layout().addLayout(l)
        self.layout().addSpacing(20)

        # Body part
        self.layout().addWidget(QtWidgets.QLabel("Limb: ", font=bold_font))
        body_widget = QtWidgets.QWidget(self)
        body_widget.setLayout(QtWidgets.QGridLayout())
        body_widget.layout().setContentsMargins(0, 0, 0, 0)
        lbl = QtWidgets.QLabel()
        lbl.setPixmap(QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'resources', 'icons', 'HalfBody.png')))
        body_widget.layout().addWidget(lbl, 0, 0, 20, 10)

        self.body_parts = {}
        for bp_name, rc in {'Head': (1, 0), 'Arm': (8, 4), 'Hand': (10, 5), 'Leg': (14, 1), 'Foot': (18, 1)}.items():
            self.body_parts[bp_name] = QtWidgets.QCheckBox('')
            body_widget.layout().addWidget(self.body_parts[bp_name], rc[0], rc[1], 1, 1)

        bt_clear = QtWidgets.QPushButton("Uncheck all")
        bt_clear.clicked.connect(lambda: self.uncheck_all(self.body_parts))
        body_widget.layout().addWidget(bt_clear, 20, 0, 1, 10)

        self.layout().addWidget(body_widget)
        self.layout().addSpacing(20)

        self.bt_map = QtWidgets.QPushButton("Submit Response")
        self.bt_map.setEnabled(False)
        self.bt_map.setMinimumHeight(40)
        self.bt_map.clicked.connect(self.submit_map)
        self.layout().addWidget(self.bt_map)

        self.layout().addSpacing(10)
        bt_clear = QtWidgets.QPushButton("Clear Channel")
        bt_clear.setMinimumHeight(20)
        bt_clear.clicked.connect(self.clear_data)
        self.layout().addWidget(bt_clear)
        self.layout().addStretch()

        # manual notes
        self.layout().addWidget(QtWidgets.QLabel("Note: ", font=bold_font))
        self.note_field = QtWidgets.QTextEdit()
        self.note_field.setMaximumHeight(80)
        self.note_field.textChanged.connect(self.check_note)
        self.layout().addWidget(self.note_field)
        self.layout().addSpacing(10)
        self.bt_note = QtWidgets.QPushButton("Submit Note")
        self.bt_note.setEnabled(False)
        self.bt_note.setMinimumHeight(20)
        self.bt_note.clicked.connect(self.submit_note)
        self.layout().addWidget(self.bt_note)
        self.layout().addStretch()

    def uncheck_all(self, d):
        for k, v in d.items():
            v.setChecked(False)

    def check_channel_and_stim(self):
        if any([x.isChecked() for x in self.channels.values()]) and \
         any([x.isChecked() for x in self.mapping_stimuli.values()]):
            self.bt_map.setEnabled(True)
        else:
            self.bt_map.setEnabled(False)

    def check_note(self):
        tmp = self.note_field.toPlainText()
        if len(tmp) > 0:
            self.bt_note.setEnabled(True)
        else:
            self.bt_note.setEnabled(False)

    def submit_map(self):
        out_dict = {}
        for chan in [s for s, c in self.channels.items() if c.isChecked()]:
            side = [s for s, c in self.sides.items() if c.isChecked()]
            if not side:
                side = ['Unspecified']

            limb = [l for l, c in self.body_parts.items() if c.isChecked()]
            if not limb:
                limb = ['Unspecified']
            out_dict[chan] = {
                'Stimuli': [s for s, c in self.mapping_stimuli.items() if c.isChecked()],
                'Sides': side,
                'Limbs': limb,
            }

        out_string = json.dumps(out_dict)
        self.map_stream.push_sample([out_string])

        # stims = ''
        # for stim, cb in self.mapping_stimuli.items():
        #     if cb.isChecked():
        #         if stim == "Custom":
        #             stims += self.custom_stimulus.text() + ','
        #         else:
        #             stims += stim + ','
        # stims = stims.rstrip(',')
        #
        # limbs = ''
        # for limb, cb in self.body_parts.items():
        #     if cb.isChecked():
        #         limbs += limb + ','
        # limbs = limbs.rstrip(',')
        #
        # for lbl, chan in self.channels.items():
        #     if chan.isChecked():
        #         if stims != '' and limbs != '':
        #             self.map_stream.push_sample([lbl, stims + '__' + limbs + ';'])
        #         else:
        #             self.map_stream.push_sample([lbl, 'Clear'])

    def submit_note(self):
        out_string = self.note_field.toPlainText()
        self.map_stream.push_sample([out_string])
        self.note_field.setPlainText("")

    def clear_data(self):
        out_dict = {}
        for chan in [s for s, c in self.channels.items() if c.isChecked()]:
            out_dict[chan] = 'Clear'

        out_string = json.dumps(out_dict)
        self.map_stream.push_sample([out_string])

    def refresh_axes(self):
        pass

    def clear(self):
        pass


class MappingGUI(CustomGUI):
    widget_cls = MappingWidget

    def __init__(self):
        self._plot_widget: MappingWidget | None = None  # This will get updated in super init but it helps type hints
        super(MappingGUI, self).__init__()
        self.setWindowTitle('MappingGUI')

    def do_plot_update(self):
        pass


