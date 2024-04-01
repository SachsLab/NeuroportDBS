from pathlib import Path

from qtpy import QtCore

from .interface import IDataSource
try:
    from cerebuswrapper import CbSdkConnection
except ModuleNotFoundError as e:
    print(e, "Try `pip install git+https://github.com/SachsLab/cerebuswrapper.git`.")


SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000"]  # , "RAW"]  RAW broken in cbsdk


class CerebusDataSource(IDataSource):

    def __init__(self, settings_path: Path, **kwargs):
        super().__init__(**kwargs)  # Sets on_connect_cb

        self._cbsdk_conn = CbSdkConnection()
        conn_params = self._cbsdk_conn.con_params.copy()

        # Get connection-level settings from common CbSdkConnection.ini
        cbsdk_settings_path = settings_path.parents[0] / "CbSdkConnection.ini"
        conn_settings = QtCore.QSettings(str(cbsdk_settings_path), QtCore.QSettings.IniFormat)
        conn_settings.beginGroup("conn-params")
        for k, t in {
            "client-addr": str,
            "client-port": int,
            "inst-addr": str,
            "inst-port": int,
            "receive-buffer-size": int
        }.items():
            conn_params[k] = conn_settings.value(k, defaultValue=conn_params[k], type=t)
        conn_settings.endGroup()
        self._cbsdk_conn.con_params = conn_params

        # Create a connection with default settings. This allows us to read config below.
        result = self._cbsdk_conn.connect()
        if result != 0:
            raise ConnectionError("Could not connect to CerebusDataSource: {}".format(result))

        conn_config = {}
        scoped_settings = QtCore.QSettings(str(settings_path), QtCore.QSettings.IniFormat)
        scoped_settings.beginGroup("data-source")
        # instance = 0, reset = True, buffer_parameter = None, range_parameter = None,
        # get_events = False, get_continuous = False, get_comments = False
        for k, t in {
            "get_continuous": bool,
            "get_events": bool,
            "get_comments": bool,
            "buffer_parameter\\comment_length": int
        }.items():
            if "\\" in k:
                split_key = k.split("\\")
                if split_key[0] not in conn_config:
                    conn_config[split_key[0]] = {}
                if split_key[0] in scoped_settings.childGroups():
                    scoped_settings.beginGroup(split_key[0])
                    conn_config[split_key[0]][split_key[1]] = scoped_settings.value(split_key[1], type=t)
                    scoped_settings.endGroup()
            else:
                if k in scoped_settings.allKeys():
                    conn_config[k] = scoped_settings.value(k, type=t)
        _sampling_rate = scoped_settings.value("sampling_rate", defaultValue=30_000, type=int)
        scoped_settings.endGroup()

        self._cbsdk_conn.cbsdk_config = conn_config  # This will trigger cbsdkConnection to update trial config
        self._group_ix = SAMPLINGGROUPS.index(str(_sampling_rate))
        self._group_info = self._decode_group_info(self._cbsdk_conn.get_group_config(self._group_ix))
        # self._wf_config = self._cbsdk_conn.get_sys_config()  # {'spklength': 48, 'spkpretrig': 10, 'sysfreq': 30000}

        if self._on_connect_cb is not None:
            self._on_connect_cb(self)

    @staticmethod
    def _decode_group_info(group_info: dict):
        for gi_item in group_info:
            gi_item['label'] = gi_item['label']
            gi_item['unit'] = gi_item['unit']
        return group_info

    @property
    def data_stats(self):
        chan_states = []
        chan_names = []
        srate = int(SAMPLINGGROUPS[self._group_ix])
        extra = {}

        # self._chan_states = pd.DataFrame(columns=['name', 'src', 'unit', 'type', 'pos'])
        for ch_ix, ch_dict in enumerate(self._group_info):
            chan_names.append(ch_dict['label'])
            ch_info = self._cbsdk_conn.get_channel_info(ch_dict['chan'])
            chan_states.append({
                'name': ch_dict['label'],
                'src': ch_dict['chan'],
                'unit': ch_dict['unit'],
                'gain': ch_dict['gain'],
                'spkthrlevel': ch_info['spkthrlevel']
            })
        # TODO: more chan_states, extra?

        return {'srate': srate, 'channel_names': chan_names, 'chan_states': chan_states, **extra}

    @property
    def is_connected(self):
        return self._cbsdk_conn.is_connected

    def get_continuous_data(self):
        return self._cbsdk_conn.get_continuous_data()

    def get_event_data(self):
        return self._cbsdk_conn.get_event_data()

    def get_comments(self):
        return self._cbsdk_conn.get_comments()

    def get_waveforms(self, chan_info):
        return self._cbsdk_conn.get_waveforms(chan_info['chan_id'])

    def disconnect_requested(self):
        self._cbsdk_conn.cbsdk_config = {'reset': True, 'get_continuous': False,
                                         'get_events': False, 'get_comments': False}
        self._cbsdk_conn.disconnect()

    def update_monitor(self, chan_info, spike_only=False):
        if not self._cbsdk_conn.is_connected:
            self._cbsdk_conn.connect()
        self._cbsdk_conn.monitor_chan(chan_info['src'], spike_only=spike_only)

    def update_threshold(self, chan_info, new_value):
        if not self._cbsdk_conn.is_connected:
            self._cbsdk_conn.connect()
        self._cbsdk_conn.set_channel_info(chan_info['chan_id'], {'spkthrlevel': new_value})

    def set_recording_state(self, on_off, file_info):
        if not self._cbsdk_conn.is_connected:
            self._cbsdk_conn.connect()
        return self._cbsdk_conn.set_recording_state(on_off, file_info)
