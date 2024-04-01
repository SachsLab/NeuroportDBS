from qtpy import QtCore
from ..settings import parse_ini_try_numeric


class MerDepthSource:
    def __init__(self, scale_factor=1.0, offset=0.0):
        # scale_factor should be 0.001 for FHC DDU V2, 1.0 otherwise.
        self.scale_factor = scale_factor
        self.offset = offset
        self.do_open()

    def do_open(self):
        raise NotImplementedError()

    def do_close(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError
