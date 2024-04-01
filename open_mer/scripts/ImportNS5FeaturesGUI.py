# Imports
from neo.rawio import BlackrockRawIO
import os
import sys
import datetime
import re
import numpy as np
from open_mer.dbsgui.widgets.SettingsDialog import SettingsDialog
from qtpy.QtWidgets import QProgressDialog
from qtpy.QtCore import Qt
from serf.tools.db_wrap import DBWrapper


class NS5OfflinePlayback:
    def __init__(self, sub_id, proc_id, f_name):
        self.f_name = f_name
        self.reader = BlackrockRawIO(f_name, nsx_to_load=5)

        self.db_wrapper = DBWrapper()

        # signal settings
        self.SR = None
        self.channels = []
        self.depths = []
        self.depth_times = []
        self.rec_start_time = None
        self.prepare_depth_values()

        # settings
        self.subject_settings = {'id': sub_id}
        self.procedure_settings = {'target_name': None,
                                   'type': 'surgical'}
        self.buffer_settings = {'sampling_rate': 30000,
                                'buffer_length': '6.000',
                                'sample_length': '4.000',
                                'delay_buffer': '0.500',
                                'overwrite_depth': True,
                                'run_buffer': False,
                                'electrode_settings': {}}
        self.procedure_name = 'Proc' + str(proc_id)

        for electrode in self.channels:
            self.buffer_settings['electrode_settings'][electrode] = {'threshold': True,
                                                                     'validity': 90.0}
        self.features_settings = {}

        # manage settings and start process
        self.manage_settings()

    def prepare_depth_values(self):
        self.reader.parse_header()

        # channels
        self.channels = [x[0] for x in self.reader.header['signal_channels']]
        self.SR = self.reader.header['signal_channels'][0][2]
        self.rec_start_time = self.reader.raw_annotations['blocks'][0]['rec_datetime']

        # comments
        rexp = re.compile(r'[a-zA-Z]*\:?(?P<depth>\-?\d*\.\d*)')
        for com in self.reader.nev_data['Comments'][0]:
            # some comments aren't depth related
            tmp_match = rexp.match(com[5].decode('utf-8'))
            if tmp_match:
                # older files marked depths at regular intervals and not only when it changed
                # we need to keep only new depth values
                d = float(tmp_match.group('depth'))
                if len(self.depths) == 0 or d != self.depths[-1]:
                    self.depth_times.append(com[0])
                    self.depths.append(d)

    def manage_settings(self):
        win = SettingsDialog(self.subject_settings,
                             self.procedure_settings,
                             self.buffer_settings,
                             self.features_settings)

        win.update_settings()
        win.close()

        sub_id = self.db_wrapper.load_or_create_subject(self.subject_settings)

        if sub_id == -1:
            print("Subject not created.")
            return False
        else:
            self.subject_settings['subject_id'] = sub_id
            self.procedure_settings['subject_id'] = sub_id
            self.procedure_settings['target_name'] = self.procedure_name
            proc_id = self.db_wrapper.load_or_create_procedure(self.procedure_settings)

            self.buffer_settings['procedure_id'] = proc_id
            self.features_settings['procedure_id'] = proc_id

        self.process_data()

    def process_data(self):
        # get settings
        buffer_length = int(float(self.buffer_settings['buffer_length']) * self.SR)
        sample_length = int(float(self.buffer_settings['sample_length']) * self.SR)
        valid_thresh = [int(x['validity'] / 100 * sample_length)
                        for x in self.buffer_settings['electrode_settings'].values()]

        bar = QProgressDialog('Processing', 'Stop', 0, len(self.depths), None)
        bar.setWindowModality(Qt.WindowModal)
        bar.show()
        # loop through each comment time and check whether segment is long enough
        for idx, (time, depth) in enumerate(zip(self.depth_times[:-1], self.depths[:-1])):
            bar.setValue(idx)
            bar.setLabelText(self.f_name + "  " + str(depth))
            if bar.wasCanceled():
                break

            if self.depth_times[idx + 1] - time >= sample_length:
                # get sample first, if doesn't pass validation, move forward until it does
                # or until buffer_length is elapsed.
                data = self.reader.get_analogsignal_chunk(i_start=time, i_stop=time + sample_length).T
                valid = self.validate_data_sample(data)
                t_offset = 0
                while not all(np.sum(valid, axis=1) > valid_thresh) and \
                        t_offset + sample_length < buffer_length and \
                        time + t_offset + sample_length < self.depth_times[idx + 1]:
                    t_offset += 300  # roughly a 100 Hz update rate.
                    data = self.reader.get_analogsignal_chunk(i_start=time + t_offset,
                                                              i_stop=time + t_offset + sample_length).T
                    valid = self.validate_data_sample(data)

                # send to db
                self.db_wrapper.save_depth_datum(depth=depth,
                                                 data=data,
                                                 is_good=np.sum(valid, axis=1) > valid_thresh,
                                                 group_info=self.channels,
                                                 start_time=self.rec_start_time +
                                                 datetime.timedelta(seconds=(time + t_offset) / self.SR),
                                                 stop_time=self.rec_start_time +
                                                 datetime.timedelta(seconds=(time + t_offset +
                                                                             sample_length) /
                                                                    self.SR))
        bar.close()

    @staticmethod
    def validate_data_sample(data):
        # TODO: implement other metrics
        # SUPER IMPORTANT: when cbpy returns an int16 value, it can be -32768, however in numpy:
        #     np.abs(-32768) = -32768 for 16 bit integers since +32768 does not exist.
        # We therefore can't use the absolute value for the threshold.
        threshold = 30000  # arbitrarily set for now
        validity = (-threshold < data) & (data < threshold)

        return validity


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication

    qapp = QApplication(sys.argv)

    # id_re = re.compile(r"(?P<Date>\d+\-\d+\-\d+)_(?P<Id>\d+)\-(?P<Proc>\d+)")
    id_re = re.compile(r"(?P<Date>\d{4}[-_]?\d{2}[-_]?\d{2})[_-]+(?P<Id>\d+)[-_]?(?P<Proc>\d+).ns5")

    base_dir = 'D:\\Sachs_Lab\\Data\\DBS'
    files_dict = {}

    for root, dirs, files in os.walk(base_dir, topdown=False):
        ns5 = [x for x in files if x.endswith('.ns5')]
        if ns5:
            for n in ns5:
                matches = id_re.match(n)
                subject_id = matches.group('Id')
                proc_id = matches.group('Proc')

                if subject_id not in files_dict:
                    files_dict[subject_id] = []
                files_dict[subject_id].append([proc_id, os.path.join(root, n.replace('.ns5', ''))])

    # select file
    for sub, ns in files_dict.items():
        for p, f in ns:
            NS5OfflinePlayback(sub, p, f)
