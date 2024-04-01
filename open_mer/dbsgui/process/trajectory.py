import time
import json
import typing

import numpy as np
import zmq
from cerebuswrapper import CbSdkConnection
from django.utils import timezone
from serf.tools.db_wrap import DBWrapper

from open_mer.data_source.cerebus import SAMPLINGGROUPS


class SnippetWorker:

    def __init__(self, ipc_settings, buffer_settings, procedure_id: typing.Optional = None):
        self._ipc_settings = ipc_settings
        self._buffer_settings = buffer_settings
        self.buffer = None
        self.db_wrapper = DBWrapper()
        self.procedure_id = None
        if procedure_id is not None:
            self.reset_procedure(procedure_id)

        # cbSDK; connect using default parameters
        self.cbsdk_conn = CbSdkConnection(simulate_ok=False)
        self.cbsdk_conn.connect()

        self._setup_ipc()

        self._reset_group_info()
        self.reset_buffer()

        self.start_time = timezone.now()
        self._snippet_sock.send_string(f"snippet_status startup")
        self.is_running = True

    def _setup_ipc(self):
        self._ipc_context = zmq.Context()

        # procedure settings subscription
        self._ctrl_sock = self._ipc_context.socket(zmq.SUB)
        self._ctrl_sock.connect(f"tcp://localhost:{self._ipc_settings['procedure_settings']}")
        self._ctrl_sock.setsockopt_string(zmq.SUBSCRIBE, "procedure_settings")

        # ddu depth subscription
        self._ddu_sock = self._ipc_context.socket(zmq.SUB)
        self._ddu_sock.connect(f"tcp://localhost:{self._ipc_settings['ddu']}")
        self._ddu_sock.setsockopt_string(zmq.SUBSCRIBE, "ddu")

        # self status publisher
        self._snippet_sock = self._ipc_context.socket(zmq.PUB)
        self._snippet_sock.bind(f"tcp://*:{self._ipc_settings['snippet_status']}")

    def _reset_group_info(self):
        self.sampling_rate = self._buffer_settings["sampling_group"]  # TODO: Fix name in FeaturesGUI.ini
        self.sampling_group = SAMPLINGGROUPS.index(str(self.sampling_rate))
        self.group_info = self.cbsdk_conn.get_group_config(self.sampling_group)
        self.n_chan = len(self.group_info)
        self.valid_electrodes = [_["chan"] for _ in self.group_info]
        self.buffer_length = int(self.sampling_rate * self._buffer_settings["buffer_duration"])
        self.sample_length = int(self.sampling_rate * self._buffer_settings["sample_duration"])
        self.delay_length = int(self.sampling_rate * self._buffer_settings["delay_duration"])
        self.overwrite_depth = self._buffer_settings["overwrite_depth"]
        # default values, might be overwritten by electrode_settings
        self.validity_threshold = [self.sample_length * self._buffer_settings["validity_threshold"]] * self.n_chan
        self.threshold = [False] * self.n_chan

    def reset_buffer(self):
        self.buffer = np.zeros((self.n_chan, self.buffer_length), dtype=np.int16)
        self.buffer_idx = 0
        # for each channel we will keep a bool array whether each sample point is valid or not
        # when a condition is met to trigger sending the sample to the DB we will pick the window
        # with highest validity count.
        self.validity = np.zeros((self.n_chan, self.buffer_length), dtype=bool)
        self.valid_idx = (0, 0)

        self.delay_counter = 0
        self.update_buffer_status = True
        self.delay_done = False

    def process_settings(self, sett_dict):
        # process inputs
        sett_keys = list(sett_dict.keys())

        if "procedure" in sett_keys and "procedure_id" in sett_dict["procedure"]:
            self.reset_procedure(sett_dict["procedure"]["procedure_id"])

        if "sampling_group_id" in sett_keys:
            # TODO: buffer_settings has bad key name because of the error in FeaturesGUI.ini
            self._buffer_settings["sampling_group"] = sett_dict["sampling_rate"]
            # self._buffer_settings["validity_threshold"] = sett_dict["???"]
            self._reset_group_info()
            self.reset_buffer()

        if "buffer" in sett_keys and "electrode_settings" in sett_dict["buffer"]:
            for ii, info in enumerate(self.group_info):
                label = info["label"]
                if label in sett_dict["buffer"]["electrode_settings"]:
                    el_sett = sett_dict["buffer"]["electrode_settings"][label]
                    self.threshold[ii] = bool(el_sett["threshold"])
                    self.validity_threshold[ii] = float(el_sett["validity"]) / 100 * self.sample_length

    def reset_procedure(self, proc_id):
        self.procedure_id = proc_id
        self.db_wrapper.select_procedure(self.procedure_id)
        print(f"Trajectory snippet updated procedure_id to {self.procedure_id}")

    def clear_buffer(self):
        if self.buffer is None:
            self.reset_buffer()
        self.buffer.fill(0)
        self.buffer_idx = 0

        self.validity.fill(False)
        # list of tuples: (index of validity value, value)
        # saves the index with largest validity across all channels
        self.valid_idx = (0, 0)
        self.delay_counter = 0

        self.update_buffer_status = True
        self.delay_done = False
        # self.start_time = timezone.now()

    def wait_for_delay_end(self, data):
        data_length = data[0][1].shape[0]
        self.delay_counter += data_length
        # check if we have accumulated enough data to end delay and start recording
        if self.delay_counter <= self.delay_length:
            return False
        else:
            # truncate the data to the first index over the delay period
            start_idx = max(0, int(self.delay_length - self.delay_counter))
            for chan_idx, (chan, values) in enumerate(data):
                data[chan_idx][1] = values[start_idx:]

            # now is for the last sample. subtract data length / SAMPLINGRATE to get time of first sample
            self.start_time = timezone.now()
            time_delta = timezone.timedelta(seconds=data[0][1].shape[0] / self.sampling_rate)
            self.start_time -= time_delta

            self._snippet_sock.send_string(f"snippet_status recording")
            return True

    def send_to_db(self, depth):
        do_save = self.valid_idx[1] != 0
        # if we actually have a computed validity (i.e. segment is long enough)
        if do_save:
            # the info that needs to be sent the DB_wrapper is:
            #   Datum:
            #       - subject_id
            #       - is_good : to be determined by validity values
            #       - start_time / stop_time ?
            #   Datum Store:
            #       - channel_labels : from group_info
            #       - erp : actual data
            #       - n_channels and n_samples : determined by data size
            #       - x_vec: time ?
            #   DatumDetailValue:
            #       - detail_type: depth (fetch from DetailType
            #       - value: depth value
            print(f"Saving depth datum. group_info: {self.group_info}")
            self.db_wrapper.save_depth_datum(depth=depth,
                                             data=self.buffer[:,
                                                              self.valid_idx[0]:self.valid_idx[0]+self.sample_length],
                                             is_good=np.array([x >= y for x, y in zip(
                                                 np.sum(self.validity[:, self.valid_idx[0]:
                                                        self.valid_idx[0] + self.sample_length], axis=1),
                                                 self.validity_threshold)], dtype=bool),
                                             group_info=self.group_info,
                                             start_time=self.start_time,
                                             stop_time=timezone.now())
        self.update_buffer_status = False
        return do_save

    @staticmethod
    def validate_data_sample(data):
        # TODO: implement other metrics
        # SUPER IMPORTANT: when cbpy returns an int16 value, it can be -32768, however in numpy:
        #     np.abs(-32768) = -32768 for 16 bit integers since +32768 does not exist.
        # We therefore can't use the absolute value for the threshold.
        threshold = 30000  # arbitrarily set for now
        validity = np.array([-threshold < x < threshold for x in data])

        return validity

    def run_forever(self):
        prev_status = None
        current_depth = None
        while self.is_running:
            try:
                received_msg = self._ctrl_sock.recv_string(flags=zmq.NOBLOCK)[len("procedure_settings") + 1:]
                settings_dict = json.loads(received_msg)
                # Check for kill signal
                if "running" in settings_dict and not settings_dict["running"]:
                    self.is_running = False
                    continue
                # Process remaining settings
                self.process_settings(settings_dict)
            except zmq.ZMQError:
                pass

            # collect NSP data, regardless of recording status to keep cbsdk buffer empty
            # data is a list of lists.
            # 1st level is a list of channels
            # 2nd level is a list [chan_id, np.array(data)]
            data = self.cbsdk_conn.get_continuous_data()
            # Only keep channels within our sampling group
            data = [x for x in data if x[0] in self.valid_electrodes]

            # only process the NSP data if Central is recording
            _status = "recording" if self.cbsdk_conn.get_recording_state() else "notrecording"
            if _status == "recording" and data and current_depth is not None:

                if not self.delay_done:
                    self.delay_done = self.wait_for_delay_end(data)

                # Only process if we are in a new depth, past the delay, and we didn't just send a snippet to the db.
                if self.delay_done and self.update_buffer_status:
                    # all data segments should have the same length, so first check if we run out of buffer space
                    data_length = data[0][1].shape[0]
                    if (self.buffer_idx + data_length) >= self.buffer_length:
                        # if we run out of buffer space before data has been sent to the DB few things could have gone
                        # wrong:
                        #   - data in buffer is not good enough
                        #   - the new data chunk is larger than the difference between buffer and sample length
                        #       (e.g. 6s buffer and 4s sample, if the current buffer has 3s of data and it receives a 4s
                        #       long chunk then the buffer would overrun, and still not have enough data to send to DB.
                        #       Although unlikely in real-life, it happened during debugging.)

                        # trim data to only fill the buffer, discarding the rest
                        # TODO: is this the optimal solution? Slide buffer instead?
                        data_length = self.buffer_length - self.buffer_idx

                    # continue to validate received data
                    for chan_idx, (chan, values) in enumerate(data):

                        if data_length > 0:
                            # Validate data
                            valid = self.validate_data_sample(values[:data_length])

                            # append data to buffer
                            self.buffer[chan_idx,
                            self.buffer_idx:self.buffer_idx + data_length] = values[:data_length]

                            self.validity[chan_idx,
                            self.buffer_idx:self.buffer_idx + data_length] = valid

                            _status = "accumulating"

                    # increment buffer index, all data segments should have same length, if they don't, will match
                    # the first channel
                    self.buffer_idx += data_length

                    # check if data length > sample length
                    if self.buffer_idx >= self.sample_length:

                        # compute total validity of last sample_length and if > threshold, send to DB
                        sample_idx = self.buffer_idx - self.sample_length

                        temp_sum = [np.sum(x[sample_idx:self.buffer_idx]) for x in self.validity]

                        # check if validity is better than previous sample, if so, store it
                        if np.sum(temp_sum) > self.valid_idx[1]:
                            self.valid_idx = (sample_idx, np.sum(temp_sum))

                        if all(x >= y for x, y in zip(temp_sum, self.validity_threshold)) or \
                                self.buffer_idx >= self.buffer_length:
                            # We have accumulated enough data for this depth. Send to db!
                            stored = self.send_to_db(current_depth)
                            if stored:
                                _status = "done"

            # check for new depth
            # At this point, the individual channels have either been sent to the DB or are still collecting waiting for
            # either of the following conditions: acquire sufficient data (i.e. sample_length) or acquire sufficiently
            # clean data (i.e. validity_threshold). If the channel is still acquiring data but has sufficiently long
            # segments, we will send the cleanest segment to the DB (i.e. valid_idx).
            new_depth = None
            try:
                received_msg = self._ddu_sock.recv_string(flags=zmq.NOBLOCK)[len("ddu") + 1:]
                if received_msg:
                    new_depth = float(received_msg)
            except zmq.ZMQError:
                pass

            # If new depth value
            if new_depth is not None and (new_depth != current_depth or self.overwrite_depth):
                # We are moving on. If still updating the buffer, then we can check to see if we have
                #  enough valid samples -- though maybe not high quality -- and save the best available segment.
                if self.update_buffer_status:
                    _ = self.send_to_db(current_depth)

                # New depth verified. Let's clear the buffer for accumulation again.
                self.clear_buffer()
                current_depth = new_depth

            if prev_status is None:
                # First iteration -- triggers an update from the ProcedureGUI if running
                self._snippet_sock.send_string(f"snippet_status refresh")

            # Optionally publish the recording status
            # if status has changed, but not from done->recording as done implies recording,
            #  and we prefer to keep the "done" status until there's a new depth.
            if _status != prev_status and not (prev_status == "done" and _status == "recording"):
                self._snippet_sock.send_string(f"snippet_status {_status}")
                prev_status = _status

            time.sleep(.010)
