import time
from .lsl import LSLDataSource
from .cerebus import CerebusDataSource


def get_now_time(data_class="CerebusDataSource"):
    """
    Returns: Device time in whatever units the device likes.
    """
    if data_class == "CerebusDataSource":
        from cerebuswrapper import CbSdkConnection
        # Attempt to synchronize different series using machine time.
        cbsdk_conn = CbSdkConnection()
        if cbsdk_conn.is_connected:
            now = cbsdk_conn.time()
        else:
            now = None
    else:
        now = time.time()
    return now
