import json
from pathlib import Path
import time
import typing

import typer
import zmq
from serf.tools.db_wrap import DBWrapper

from open_mer.scripts.Snippets_Process import build_ini_paths, parse_ini


class FeaturesWorker:

    def __init__(self, ipc_settings, buffer_settings, feature_settings, procedure_id: typing.Optional = None):
        self._ipc_settings = ipc_settings
        self._buffer_settings = buffer_settings
        self._feature_settings = feature_settings

        # DB wrapper
        self.db_wrapper = DBWrapper()

        self._setup_ipc()

        self.procedure_id = None
        self.last_datum_id = 0  # fetch datum ids greater than this value

        self._select_procedure(procedure_id)

        self.is_running = True

    def _setup_ipc(self):
        self._ipc_context = zmq.Context()

        # procedure settings subscription
        self._ctrl_sock = self._ipc_context.socket(zmq.SUB)
        self._ctrl_sock.connect(f"tcp://localhost:{self._ipc_settings['procedure_settings']}")
        self._ctrl_sock.setsockopt_string(zmq.SUBSCRIBE, "procedure_settings")

    def _select_procedure(self, procedure_id: typing.Optional[int] = None):
        if procedure_id is None:
            # Get the 0th subject and the -1th procedure for that subject
            sub_id = list(self.db_wrapper.list_all_subjects())[0]
            subj_details = self.db_wrapper.load_subject_details(sub_id)
            self.db_wrapper.select_subject(subj_details["subject_id"])
            proc = list(self.db_wrapper.list_all_procedures(subj_details["subject_id"]))[-1]
        else:
            self.db_wrapper.select_procedure(procedure_id)
            proc = self.db_wrapper.current_procedure
        sett_dict = {
            "procedure": {"procedure_id": proc.procedure_id},
            "features": [v[0] for k, v in self._feature_settings.items() if v[1]]
        }
        self.process_settings(sett_dict)

    def process_settings(self, sett_dict):
        # process inputs
        if 'procedure' in sett_dict.keys():
            self.reset_procedure(sett_dict['procedure'])

        if 'features' in sett_dict.keys():
            self.reset_features(sett_dict['features'])

    def reset_procedure(self, proc_dict):
        if "procedure_id" in proc_dict:
            self.procedure_id = proc_dict["procedure_id"]
            self.db_wrapper.select_procedure(self.procedure_id)
            self.reset_datum()

    def reset_features(self, feats):
        self.db_wrapper.select_features(feats)
        self.reset_datum()

    def reset_datum(self):
        # we will list all datum for the subject and all feature types that match the settings
        self.last_datum_id = 0

    def run_forever(self):
        while self.is_running:
            try:
                received_msg = self._ctrl_sock.recv_string(flags=zmq.NOBLOCK)[len("procedure_settings")+1:]
                settings_dict = json.loads(received_msg)
                if "running" in settings_dict and not settings_dict["running"]:
                    self.is_running = False
                    continue
                self.process_settings(settings_dict)
            except zmq.ZMQError:
                pass

            new_data = list(self.db_wrapper.list_all_datum_ids(gt=self.last_datum_id))

            while len(new_data) > 0:
                print(f"Calculating features for {len(new_data)} remaining segments...")
                # get oldest data and check if all features have been computed
                d_id = new_data.pop(0)
                if self.db_wrapper.check_and_compute_features(d_id):
                    # If process was successful then update last_datum_id
                    self.last_datum_id = max(d_id, self.last_datum_id)
            time.sleep(0.25)  # test to slow down process to decrease HDD load
            # time.sleep(0.1)


def main(ini_path: typing.Optional[Path] = None, procedure_id: typing.Optional[int] = None):
    ini_paths = build_ini_paths()
    if ini_path is not None:
        ini_paths.append(ini_path)
    ipc_settings, buffer_settings, feature_settings = parse_ini(ini_paths)
    worker = FeaturesWorker(ipc_settings, buffer_settings, feature_settings, procedure_id=procedure_id)
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        worker.is_running = False


if __name__ == '__main__':
    typer.run(main)
