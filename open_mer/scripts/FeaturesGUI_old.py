import os
import sys
import numpy as np
from qtpy import QtCore, QtWidgets, QtGui
from cerebuswrapper import CbSdkConnection

# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from open_mer.dbsgui.widgets.custom import CustomGUI, CustomWidget
from open_mer.feature_plots import *
from open_mer.dbsgui.widgets.SettingsDialog import SettingsDialog

from serf.tools.db_wrap import DBWrapper, ProcessWrapper

# Settings
from open_mer.settings.defaults import uVRANGE, BASEPATH, SAMPLINGRATE, \
    BUFFERLENGTH, SAMPLELENGTH, DELAYBUFFER, OVERWRITEDEPTH, DEPTHSETTINGS


# TODO: Rewrite FeaturesGUI so it doesn't inherit from CustomGUI
#  Non-patient settings from INI (including data-source, but only used for recording_mirror)
#  Build UI
#  Launch modal settings window on startup
#  Manage sub-processes
#  All data interaction (other than starting stopping recording_mirror) should happen through DB


class FeaturesGUI(CustomGUI):

    def __init__(self):
        # settings dictionaries
        self.subject_settings = {}
        self.procedure_settings = {}
        self.features_settings = {}

        super().__init__()
        # Calls restore_from_settings
        # -->   Eventually try_reset_widget will be called and allowed to proceed because both
        #       self.data_source (set via on_source_connected cb) and
        #       self.plot_config (setter at end of restore_from_settings are both set.
        # -->   Creates self._plot_widget = widget_cls(self.data_source.data_stats, **self.plot_config)
        self.setWindowTitle('FeaturesGUI')

        # DB wrapper
        self.db_wrapper = DBWrapper()

    @CustomGUI.widget_cls.getter
    def widget_cls(self):
        return FeaturesPlotWidget

    def on_plot_closed(self):
        if self.plot_widget:
            self.plot_widget.kill_processes()

            if self.plot_widget.awaiting_close:
                del self.plot_widget

        QtWidgets.QApplication.instance().quit()

    # defined in the CustomGUI class, is triggered when the "Add Plot" button
    # is pressed in the default GUI (Connect, Add Plot, Quit)
    def on_action_add_plot_triggered(self):
        # Get all the available information for settings
        # NSP info, None if not connected
        sampling_group_id = SAMPLINGGROUPS.index(str(SAMPLINGRATE))
        self.group_info = self.cbsdk_conn.get_group_config(sampling_group_id)

        # we only need to set the default values for the depth buffer here since it requires electrode
        # information. The rest accepts empty dicts
        self._plot_config['buffer']['sampling_rate'] = SAMPLINGRATE
        self._plot_config['buffer']['sampling_group_id'] = sampling_group_id
        self._plot_config['buffer']['buffer_length'] = '{:.3f}'.format(BUFFERLENGTH)
        self._plot_config['buffer']['sample_length'] = '{:.3f}'.format(SAMPLELENGTH)
        self._plot_config['buffer']['delay_buffer'] = '{:.3f}'.format(DELAYBUFFER)
        self._plot_config['buffer']['overwrite_depth'] = OVERWRITEDEPTH
        self._plot_config['buffer']['electrode_settings'] = {}

        if self.group_info:
            for electrode in self.group_info:
                self._plot_config['buffer']['electrode_settings'][electrode['label'].decode('utf-8')] = DEPTHSETTINGS

        # Open settings dialog and update DBWrapper subject and settings dicts
        if not self.manage_settings():
            return

        self._plot_widget.call_manage_settings.connect(self.get_settings)

        # send values to widgets
        self.send_settings()

    def do_plot_update(self):
        # since all widgets have different use, they will each handle their own data collection.
        self._plot_widget.update()

    def manage_settings(self):
        # Open prompt to input subject details
        win = SettingsDialog(self.subject_settings,
                             self.procedure_settings,
                             self._plot_config['buffer'],
                             self.features_settings)
        result = win.exec_()
        if result == QtWidgets.QDialog.Accepted:
            win.update_settings()
        else:
            return False

        # Create or load subject
        # Returns subject_id/-1 whether subject is properly created or not
        sub_id = self.db_wrapper.load_or_create_subject(self.subject_settings)

        if sub_id == -1:
            print("Subject not created.")
            return False
        else:
            self.subject_settings['subject_id'] = sub_id
            self.procedure_settings['subject_id'] = sub_id
            proc_id = self.db_wrapper.load_or_create_procedure(self.procedure_settings)

            self._plot_config['buffer']['procedure_id'] = proc_id
            self.features_settings['procedure_id'] = proc_id

            return True

    def get_settings(self):
        # open prompt and update values
        if self.manage_settings():
            # update values to widgets
            self.send_settings()

    def send_settings(self):
        self.plot_widget.process_settings(self.subject_settings,
                                          self.procedure_settings,
                                          self._plot_config['buffer'],
                                          self.features_settings)


class FeaturesPlotWidget(CustomWidget):

    def __init__(self, *args, **kwargs):

        # Settings
        self.subject_settings = None
        self.procedure_settings = None
        self.depth_settings = None
        self.features_settings = None

        # Plot options
        self.plot_config = {}
        self.plot_stack = QtWidgets.QStackedWidget()
        # generate a dict {chan_label: {Feature:[stack idx, latest_datum]}}
        self.stack_dict = {}

        # wrap up init
        super().__init__(*args, **kwargs)

        # initialize plots
        self.layout().addWidget(self.plot_stack)
        self.refresh_axes()  # Extra time on purpose.

        # Define and start processes
        # will only start processes when settings are received
        self.depth_wrapper = ProcessWrapper('Depth_Process')
        self.depth_process_running = False

        self.features_wrapper = ProcessWrapper('Features_Process')
        self.features_process_running = False

    def process_settings(self, sub_sett, proc_sett, depth_sett, feat_sett):
        self.subject_settings = dict(sub_sett)
        self.procedure_settings = dict(proc_sett)
        self.depth_settings = dict(depth_sett)
        self.features_settings = dict(feat_sett)

        # validate that we have some data in the electrode_settings. If the NSP is not connected we will have
        # to load the channel names from the DB. Also we want to keep the FeaturesGUI unaware of the DB channels.
        if len(self.depth_settings['electrode_settings']) == 0:
            self.depth_settings['electrode_settings'] = {}
            for lbl in DBWrapper().list_channel_labels():
                self.depth_settings['electrode_settings'][lbl] = DEPTHSETTINGS
            CbSdkConnection().is_simulating = True

        # set new features
        self.feature_select.setCurrentIndex(0)  # Raw
        while self.feature_select.count() > 2:  # Raw and Mapping
            self.feature_select.removeItem(2)
        self.feature_select.addItems(self.features_settings['features'].keys())

        # set new channels
        self.chan_select.setCurrentIndex(0)  # None
        while self.chan_select.count() > 1:
            self.chan_select.removeItem(1)
        self.chan_select.addItems(self.depth_settings['electrode_settings'].keys())

        # clear and update stacked widget
        to_delete = [self.plot_stack.widget(x) for x in range(self.plot_stack.count())]
        for wid in to_delete:
            self.plot_stack.removeWidget(wid)
            wid.deleteLater()
            wid = None
        self.stack_dict = {}
        self.create_plots()

        self.depth_wrapper.send_settings(self.depth_settings)
        self.features_wrapper.send_settings(self.features_settings)

        if not self.features_process_running:
            self.manage_feature_process(True)

        # self.clear()
        self.read_from_shared_memory()

    def clear(self):
        # set the current datum of all stacks to 0
        for lbl in self.stack_dict:
            for feat in self.stack_dict[lbl]:
                self.stack_dict[lbl][feat][1] = 0
                self.plot_stack.widget(self.stack_dict[lbl][feat][0]).clear_plot()

    def update(self):
        # features plot
        curr_chan_lbl = self.chan_select.currentText()
        if curr_chan_lbl != 'None':
            curr_feat = self.feature_select.currentText()
            do_hp = self.do_hp.isChecked()

            if do_hp != self.plot_stack.currentWidget().plot_config['do_hp'] or \
                    self.y_range != self.plot_stack.currentWidget().plot_config['y_range']:
                self.plot_stack.currentWidget().clear_plot()
                self.stack_dict[curr_chan_lbl][curr_feat][1] = 0
                self.plot_stack.currentWidget().plot_config['do_hp'] = do_hp
                self.plot_stack.currentWidget().plot_config['y_range'] = self.y_range

            curr_datum = self.stack_dict[curr_chan_lbl][curr_feat][1]
            if curr_feat == 'Raw':
                all_data = DBWrapper().load_depth_data(chan_lbl=curr_chan_lbl,
                                                       gt=curr_datum,
                                                       do_hp=do_hp,
                                                       return_uV=True)
            elif curr_feat == 'Mapping':
                all_data = DBWrapper().load_mapping_response(chan_lbl=curr_chan_lbl,
                                                             gt=curr_datum)
            else:
                all_data = DBWrapper().load_features_data(category=curr_feat,
                                                          chan_lbl=curr_chan_lbl,
                                                          gt=curr_datum)
            if all_data:
                self.plot_stack.currentWidget().update_plot(dict(all_data))
                self.stack_dict[curr_chan_lbl][curr_feat][1] = max(all_data.keys())

def main():
    _ = QtWidgets.QApplication(sys.argv)
    window = FeaturesGUI()
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()


if __name__ == '__main__':
    main()
