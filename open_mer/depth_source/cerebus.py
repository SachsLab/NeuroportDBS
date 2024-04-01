from .base import MerDepthSource
try:
    from cerebuswrapper import CbSdkConnection
except ModuleNotFoundError as e:
    print(e, "Try `pip install git+https://github.com/SachsLab/cerebuswrapper.git`.")


class CBSDKPlayback(MerDepthSource):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def do_open(self):
        CbSdkConnection().connect()
        CbSdkConnection().cbsdk_config = {
            'reset': True, 'get_events': False, 'get_comments': True,
            'buffer_parameter': {
                'comment_length': 10
            }
        }

    def do_close(self):
        CbSdkConnection().disconnect()

    def update(self) -> None | float:
        cbsdk_conn = CbSdkConnection()
        if cbsdk_conn.is_connected:
            comments = cbsdk_conn.get_comments()
            if comments:
                comment_strings = [x[1].decode('utf8') for x in comments]
            else:
                comment_strings = ""
            dtts = []
            for comm_str in comment_strings:
                if 'DTT:' in comm_str:
                    dtts.append(float(comm_str[4:]))
            if len(dtts) > 0:
                raw_value = dtts[-1]
                return raw_value
        return None
