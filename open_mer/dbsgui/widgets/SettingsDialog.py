import typing

import numpy as np
# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QDialog, QVBoxLayout, QWidget, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget, \
                           QCheckBox, QTabWidget, QTextEdit
from qtpy.QtCore import QDate, QRegularExpression, Qt, Signal
from qtpy.QtGui import QRegularExpressionValidator
from serf.tools.db_wrap import DBWrapper


class SubjectWidget(QWidget):
    subject_change = Signal(int)

    def __init__(self, subject_settings, parent=None):
        super().__init__(parent=parent)

        self._setup_ui()

        # Subject Settings
        self.subject_settings = subject_settings
        if not self.subject_settings:
            self.update_settings_from_db(-1)

        self.update_subj_widgets_from_settings()

    def _setup_ui(self):
        subject_layout = QGridLayout(self)
        subject_layout.setColumnMinimumWidth(2, 60)

        subject_layout.addWidget(QLabel("Id: "), 0, 0, 1, 1)
        self.id_combo = QComboBox()
        self.id_combo.setEditable(True)
        self.id_combo.addItem("")
        self.id_combo.addItems(DBWrapper().list_all_subjects())
        self.id_combo.currentIndexChanged.connect(self.load_subject)  # Which transitively calls check_subject
        self.id_combo.lineEdit().editingFinished.connect(self.check_subject)
        subject_layout.addWidget(self.id_combo, 0, 1, 1, 4)

        subject_layout.addWidget(QLabel("Name: "), 1, 0, 1, 1)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(135)
        subject_layout.addWidget(self.name_edit, 1, 1, 1, 4)

        _subj_enums = DBWrapper().return_enums("subject")
        subject_layout.addWidget(QLabel("Sex: "), 2, 0, 1, 1)
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(_subj_enums["sex"] if "sex" in _subj_enums.keys() else [])
        self.sex_combo.setCurrentIndex(0)
        subject_layout.addWidget(self.sex_combo, 2, 1, 1, 1)

        subject_layout.addWidget((QLabel("Date of birth: ")), 3, 0, 1, 1)
        self.dob_calendar = QCalendarWidget()
        subject_layout.addWidget(self.dob_calendar, 3, 1, 1, 3)

        subject_layout.addWidget(QLabel("NSP file comment: "), 4, 0, 1, 1)
        self.file_comment = QTextEdit("")
        self.file_comment.setMaximumHeight(150)
        subject_layout.addWidget(self.file_comment, 4, 1, 1, 4)

    def update_subj_widgets_from_settings(self):
        self.name_edit.setText(self.subject_settings.get("name", ""))
        self.id_combo.setCurrentText(self.subject_settings.get("id", ""))
        self.sex_combo.setCurrentText(self.subject_settings.get("sex", ""))
        dob = self.subject_settings.get("birthday", "")
        if dob not in [None, ""]:
            q_dob = QDate.fromString(dob.isoformat() if hasattr(dob, "year") else dob, "yyyy-MM-d")
            self.dob_calendar.setSelectedDate(q_dob)
        else:
            self.dob_calendar.setSelectedDate(QDate.currentDate())

    def update_settings_from_db(self, idx):
        for key, value in DBWrapper().load_subject_details(idx).items():
            self.subject_settings[key] = value

    def load_subject(self):
        # id is a unique and mandatory field
        self.check_subject()
        self.update_subj_widgets_from_settings()

    def check_subject(self):
        # when changing the id in the combobox, can be modifying or entering an existing subject id. Check to load data
        # if so.
        curr_id = self.id_combo.currentText()
        if curr_id != "":
            self.update_settings_from_db(curr_id)
            self.subject_change.emit(self.subject_settings["subject_id"])
        else:
            self.update_settings_from_db(-1)
            self.subject_change.emit(-1)

    def to_dict(self):
        self.subject_settings["id"] = self.id_combo.currentText()
        self.subject_settings["name"] = self.name_edit.text()
        self.subject_settings["sex"] = self.sex_combo.currentText()
        self.subject_settings["birthday"] = self.dob_calendar.selectedDate().toPython()
        self.subject_settings["NSP_comment"] = self.file_comment.toPlainText()


class ProcedureWidget(QWidget):
    def __init__(self, procedure_settings):
        super(ProcedureWidget, self).__init__()

        # Settings
        self.procedure_settings = procedure_settings

        # populate with defaults if empty
        if not self.procedure_settings:
            self.update_settings_from_db(None)

        self.proc_enums = DBWrapper().return_enums("procedure")
        self._setup_ui()
        self.update_proc_widgets_from_settings()

    def _setup_ui(self):
        proc_layout = QGridLayout(self)

        row = 0
        proc_layout.addWidget(QLabel("Procedure: "), row, 0, 1, 1)

        prev_proc = QComboBox()
        prev_proc.setObjectName("procedure_QComboBox")
        prev_proc.setEnabled(True)
        proc_layout.addWidget(prev_proc, row, 1, 1, 3)
        self.check_all_procedures(None, False)
        prev_proc.currentIndexChanged.connect(self.procedure_selection_change)

        row += 1
        proc_layout.addWidget(QLabel("Target name: "), row, 0, 1, 1)
        target_name = QLineEdit("")
        target_name.setObjectName("targetName_QLineEdit")
        proc_layout.addWidget(target_name, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Type: "), row, 0, 1, 1)
        type_combo = self.combo_from_enum("type")
        type_combo.setObjectName("type_QComboBox")
        proc_layout.addWidget(type_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Recording configuration: "), row, 0, 1, 1)
        rec_combo = self.combo_from_enum('recording_config')
        rec_combo.setObjectName("recording_QComboBox")
        proc_layout.addWidget(rec_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Electrode configuration: "), row, 0, 1, 1)
        electrode_combo = self.combo_from_enum("electrode_config")
        electrode_combo.setObjectName("electrode_QComboBox")
        proc_layout.addWidget(electrode_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Distance to target: "), row, 0, 1, 1)
        dist_to_target = self.coord_line_edit()
        dist_to_target.setObjectName("distance_to_target_QLineEdit")
        proc_layout.addWidget(dist_to_target, row, 1, 1, 1)

        for field_name in ["Entry", "Target", "A", "E"]:
            row += 1
            proc_layout.addWidget(QLabel(f"{field_name} (x, y, z): "), row, 0, 1, 1)
            for ix, d in enumerate(["x", "y", "z"]):
                _le = self.coord_line_edit()
                _le.setObjectName(f"{field_name.lower()}_{d}_QLineEdit")
                proc_layout.addWidget(_le, row, ix + 1, 1, 1)

        row += 1
        comp_dist_to_target = QLabel("Computed distance: 0.000 mm; Difference: 0.000 mm")
        comp_dist_to_target.setObjectName("computed_QLabel")
        proc_layout.addWidget(comp_dist_to_target, row, 0, 1, 2)

        row += 1
        proc_layout.addWidget(QLabel("Offset direction: "), row, 0, 1, 1)
        offset_direction_combo = self.combo_from_enum('offset_direction')
        offset_direction_combo.setObjectName("offset_direction_QComboBox")
        proc_layout.addWidget(offset_direction_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Offset size: "), row, 0, 1, 1)
        offset_size = self.coord_line_edit()
        offset_size.setObjectName("offset_QLineEdit")
        proc_layout.addWidget(offset_size, row, 1, 1, 1)

        row += 1
        proc_layout.addWidget(QLabel("Medication status: "), row, 0, 1, 1)
        medic_combo = self.combo_from_enum("medication_status")
        medic_combo.setObjectName("medic_QComboBox")
        proc_layout.addWidget(medic_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QWidget(), row, 1, 1, 3)

    def check_all_procedures(self, subject_id, block):
        self.all_procedures = DBWrapper().list_all_procedures(subject_id)

        prev_proc: QComboBox = self.findChild(QComboBox, name="procedure_QComboBox")
        # Clear combobox and fill with a summary of each procedure
        prev_proc.blockSignals(block)
        prev_proc.clear()
        prev_proc.addItem("(new)")  # 0th item indicates a new procedure
        prev_proc.addItems([
            " ".join([
                str(x.procedure_id), x.target_name, x.recording_config, x.date.strftime('%Y-%m-%d')
            ])
            for x in self.all_procedures
        ])
        row_ix = 0
        if "procedure_id" in self.procedure_settings and self.procedure_settings["procedure_id"] is not None:
            known_ids = [_.procedure_id for _ in self.all_procedures]
            if self.procedure_settings["procedure_id"] in known_ids:
                row_ix = known_ids.index(self.procedure_settings["procedure_id"]) + 1
                prev_proc.blockSignals(False)
        prev_proc.setCurrentIndex(row_ix)
        prev_proc.blockSignals(False)

    def combo_from_enum(self, enum_name):
        combo = QComboBox()
        combo.addItems(self.proc_enums[enum_name] if enum_name in self.proc_enums.keys() else [])
        combo.setCurrentText('none')
        return combo

    def coord_line_edit(self):
        template = QRegularExpression(r"[-]?\d*\.?\d{0,3}")
        validator = QRegularExpressionValidator(template)

        line = QLineEdit("0.0")
        line.setValidator(validator)
        line.setFixedWidth(60)
        # line.editingFinished.connect(self.update_dist_to_target)
        line.textChanged.connect(self.update_dist_to_target)

        return line

    def update_dist_to_target(self, new_string):

        if new_string not in ["-", ".", "", "-."]:
            vals = np.array([
                [
                    float(self.findChild(QLineEdit, f"{fn}_{d}_QLineEdit").text())
                    for fn in ["target", "entry"]
                ]
                for d in ["x", "y", "z"]
            ])
            ddt = np.sqrt(np.sum((vals[:, 0] - vals[:, 1]) ** 2))

            dist_to_target: QLineEdit = self.findChild(QLineEdit, "distance_to_target_QLineEdit")
            diff = float(dist_to_target.text()) - ddt

            self.findChild(QLabel, "computed_QLabel").setText(
                "Computed distance: {:.3f} mm; Difference: {:.3f} mm".format(ddt, diff))

    def change_subject(self, sub_id, block=False):
        self.check_all_procedures(sub_id, block)

    def procedure_selection_change(self):
        prev_proc: QComboBox = self.findChild(QComboBox, name="procedure_QComboBox")
        id: typing.Optional[int] = None
        if prev_proc.currentIndex() > 0:
            # If the user selected a procedure other than the '(new)' procedure.
            ix = prev_proc.currentIndex() - 1  # -1 because first entry is always blank.
            id = self.all_procedures[ix].procedure_id
        self.update_settings_from_db(id)
        self.update_proc_widgets_from_settings()

    def update_settings_from_db(self, idx: typing.Optional[int]):
        res_dict = DBWrapper().load_procedure_details(idx, exclude=['subject', 'procedure_id'])
        if idx is None and bool(self.procedure_settings):
            res_dict.update(self.procedure_settings)
        res_dict["procedure_id"] = idx
        self.procedure_settings.update(res_dict)

    def update_proc_widgets_from_settings(self):
        target_name: QLineEdit = self.findChild(QLineEdit, name="targetName_QLineEdit")
        target_name.setText(self.procedure_settings.get("target_name", ""))

        type_combo: QComboBox = self.findChild(QComboBox, "type_QComboBox")
        type_combo.setCurrentText(self.procedure_settings.get("type", ""))

        rec_combo: QComboBox = self.findChild(QComboBox, "recording_QComboBox")
        rec_combo.setCurrentText(self.procedure_settings.get("recording_config", ""))

        electrode_combo: QComboBox = self.findChild(QComboBox, "electrode_QComboBox")
        electrode_combo.setCurrentText(self.procedure_settings.get("electrode_config", ""))

        medic_combo: QComboBox = self.findChild(QComboBox, name="medic_QComboBox")
        medic_combo.setCurrentText(self.procedure_settings.get("medication_status", ""))

        offset_size: QLineEdit = self.findChild(QLineEdit, name="offset_QLineEdit")
        offset_size.setText(str(self.procedure_settings.get("offset_size", None)))

        offset_direction: QComboBox = self.findChild(QComboBox, name="offset_direction_QComboBox")
        offset_direction.setCurrentText(self.procedure_settings.get("offset_direction", ""))

        for field_name in ["entry", "target", "a", "e"]:
            field_value = self.procedure_settings.get(field_name, None)
            if field_value is None:
                field_value = [0., 0., 0.]
            for d, v in zip(["x", "y", "z"], field_value):
                _txt: QLineEdit = self.findChild(QLineEdit, f"{field_name}_{d}_QLineEdit")
                _txt.setText(str(v))

        dtt = self.procedure_settings.get("distance_to_target", None)
        if dtt is None:
            dtt = 0.000
        dtt_edit: QLineEdit = self.findChild(QLineEdit, "distance_to_target_QLineEdit")
        dtt_edit.setText(str(dtt))
        # self.update_dist_to_target()

    def to_dict(self):
        type_combo = self.findChild(QComboBox, name="type_QComboBox")
        self.procedure_settings["type"] = type_combo.currentText()

        for field in ["entry", "target", "a", "e"]:
            vals = np.array([
                float(self.findChild(QLineEdit, name=f"{field}_{dim}_QLineEdit").text())
                for dim in ["x", "y", "z"]
            ], dtype=float)
            self.procedure_settings[field] = vals

        dist_to_target: QLineEdit = self.findChild(QLineEdit, "distance_to_target_QLineEdit")
        self.procedure_settings["distance_to_target"] = float(dist_to_target.text())

        electrode_combo: QComboBox = self.findChild(QComboBox, name="electrode_QComboBox")
        self.procedure_settings["electrode_config"] = electrode_combo.currentText()

        medic_combo: QComboBox = self.findChild(QComboBox, name="medic_QComboBox")
        self.procedure_settings["medication_status"] = medic_combo.currentText()

        target_name: QLineEdit = self.findChild(QLineEdit, name="targetName_QLineEdit")
        self.procedure_settings["target_name"] = target_name.text()

        rec_combo: QComboBox = self.findChild(QComboBox, name="recording_QComboBox")
        self.procedure_settings["recording_config"] = rec_combo.currentText()

        offset_direction_combo: QComboBox = self.findChild(QComboBox, "offset_direction_QComboBox")
        self.procedure_settings["offset_direction"] = offset_direction_combo.currentText()

        offset_size: QLineEdit = self.findChild(QLineEdit, name="offset_QLineEdit")
        self.procedure_settings["offset_size"] = float(offset_size.text())


class SettingsDialog(QDialog):
    def __init__(
            self,
            subject_settings: dict,  # Will be mutated by SubjectWidget!
            procedure_settings: dict,  # Will be mutated by ProcedureWidget!
            parent=None
    ):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Enter settings.")

        # Widgets to show/edit parameters.
        dialog_layout = QVBoxLayout(self)

        tab_widget = QTabWidget(self)
        self.subject_widget = SubjectWidget(subject_settings)
        tab_widget.addTab(self.subject_widget, 'Subject')

        self.proc_widget = ProcedureWidget(procedure_settings)
        tab_widget.addTab(self.proc_widget, 'Procedure')

        dialog_layout.addWidget(tab_widget)

        # signals
        self.subject_widget.subject_change.connect(self.proc_widget.change_subject)

        # update procedures when re-opening settings window
        if "subject_id" not in subject_settings.keys():
            self.subject_widget.check_subject()
        elif subject_settings["subject_id"] not in [None, ""]:
            self.proc_widget.change_subject(subject_settings["subject_id"], block=True)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        dialog_layout.addWidget(buttons, alignment=Qt.AlignHCenter)

        self.setLayout(dialog_layout)

    def update_settings(self):
        self.subject_widget.to_dict()
        self.proc_widget.to_dict()
