from qtpy.QtGui import QColor
from qtpy.QtCore import Qt

# NSP
BASEPATH = 'C:\\Recordings'  # default path for file saving
SAMPLINGRATE = 30000
SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000"]  # , "RAW"]  RAW broken in cbsdk
SIMOK = False  # Make this False for production. Make this True for development when NSP/NPlayServer are unavailable.
FILTERCONFIG = {'order': 4, 'cutoff': 250, 'type': 'highpass', 'output': 'sos'}  # high pass filter for display
DSFAC = 100  # down-sampling factor

# Range of electrodes depth in mm.
DEPTHRANGE = [-20, 5]
DEPTHTARGET = 0.0
DDUSCALEFACTOR = 1000  # Target scale is mm. FHC drive returns um

# Depth buffer
BUFFERLENGTH = 6.0  # seconds
SAMPLELENGTH = 4.0  # seconds
DELAYBUFFER = 0.5  # seconds
OVERWRITEDEPTH = True

# Window Dimensions
WINDOWDIMS_SWEEP = [0, 0, 620, 1080]
WINDOWDIMS_LFP = [1320, 250, 600, 830]
WINDOWDIMS_RASTER = [620, 0, 300, 1080]
WINDOWDIMS_WAVEFORMS = [920, 0, 300, 1080]
WINDOWDIMS_MAPPING = [1220, 0, 100, 1080]
WINDOWDIMS_DEPTH = [1320, 0, 600, 250]
WINDOWDIMS_SUBPROC = [1320, 250, 600, 150]
WINDOWDIMS_FEATURES = [1320, 400, 600, 680]
WINDOWDIMS_DICT = {
    'SweepGUI': WINDOWDIMS_SWEEP, 'RasterGUI': WINDOWDIMS_RASTER,
    'WaveformGUI': WINDOWDIMS_WAVEFORMS, 'DepthGUI': WINDOWDIMS_DEPTH,
    'ProcedureGUI': WINDOWDIMS_SUBPROC,
    'FeaturesGUI': WINDOWDIMS_FEATURES, 'MappingGUI': WINDOWDIMS_MAPPING
}

# Sensorimotor mapping
MAPPINGSTIMULI = ['Kinesthetic', 'Tactile']

# Plots
XRANGE_SWEEP = 1.05  # seconds. Purposely slightly different to 1.0 so the NSS output doesn't overlap perfectly.
XRANGE_RASTER = 0.5  # seconds
XRANGE_WAVEFORMS = [-300, 1140]  # uSeconds
XRANGE_FEATURES = [-4000, 120000]  # samples

uVRANGE = 250  # uV. y-axis range per channel, use +- this value.

YRANGE_RASTER = 8  # Number of rows.
NPLOTSRAW = 8  # number of rows in the Raw feature plots

NWAVEFORMS = 200  # Default max number of waveforms to plot.

NPLOTSEGMENTS = 20  # Divide the Sweep plot into this many segments; each segment will be updated independent of rest.

# Colors and Fonts
THEMES = {
    'dark': {
        'pencolors': ["cyan", QColor(0, 255, 0), "magenta", "red", "yellow", "white"],
        'bgcolor': Qt.black,
        'labelcolor': Qt.gray,
        'axiscolor': Qt.gray,
        'axiswidth': 1
    }
}
WF_COLORS = ["white", "magenta", "cyan", "yellow", "purple", "green"]
LABEL_FONT_POINT_SIZE = 24

# Default settings. If finds a category of features with the same name, will apply the value here.
DEPTHSETTINGS = {'threshold': True,
                 'validity': 90.0}
