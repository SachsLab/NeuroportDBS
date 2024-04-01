import typing
from typing_extensions import Self

from qtpy import QtCore


class IDataSource(QtCore.QObject):

    def __init__(self, on_connect_cb: typing.Optional[typing.Callable[[Self], None]] = None):
        super().__init__()  # QObject init required for signals to work
        self._on_connect_cb = on_connect_cb

    @property
    def data_stats(self):
        raise NotImplementedError("Sub-classes must implement this and return a dict of form\n"
                                  "{'srate': sample_rate_float,"
                                  " 'channel_names': ['list', 'of', 'str', 'channel', 'names']"
                                  " (optional) 'chan_states': list of dicts, one for each channel. See IRenderer."
                                  "}")

    def disconnect_requested(self):
        raise NotImplementedError("Sub-classes must implement a `disconnect_requested` method.")

    def get_continuous_data(self):
        raise NotImplementedError("Sub-classes must implement a `get_continuous_data` method.")

    def get_event_data(self):
        raise NotImplementedError("Sub-classes must implement a `get_event_data` method.")

    def get_comments(self):
        raise NotImplementedError("Sub-classes must implement a `get_comments` method.")

    def update_monitor(self, chan_info, spike_only=False):
        raise NotImplementedError("Sub-classes must implement a `update_monitor` method.")

    def update_threshold(self, chan_info, new_value):
        raise NotImplementedError("Sub-classes must implement a `update_threshold` method.")

    def set_recording_state(self, on_off, file_info):
        raise NotImplementedError("Sub-classes must implement a `set_recording_state` method.")
