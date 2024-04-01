# Just some chunks of code to help with development.
import sys, os
import time
open_mer_path = os.path.abspath(os.path.join('..', 'OpenMER', 'neuroport_dbs'))
sys.path.append(open_mer_path)
from cerebuswrapper import CbSdkConnection

SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000", "RAW"]

cbsdk_conn = CbSdkConnection(simulate_ok=False)
cbsdk_conn.connect()
cbsdk_conn.cbsdk_config = {
    'reset': True, 'get_events': False, 'get_comments': False, 'get_continuous': False,
    'buffer_parameter': {
        'comment_length': 0
    }
}
group_info = cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))
sys_config = cbsdk_conn.get_sys_config()

# temp_ev = cbsdk_conn.get_event_data()
# temp_cont = cbsdk_conn.get_continuous_data()

chid = group_info[0]['chan']
temp_wfs, unit_ids = cbsdk_conn.get_waveforms(chid)

# import matplotlib.pyplot as plt
# plt.ion()
# plt.plot(temp_wfs[unit_ids == 3].T)

cbsdk_conn.disconnect()
