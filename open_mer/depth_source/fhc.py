import re
# serial imports happen in methods
from .base import MerDepthSource


class FHCSerial(MerDepthSource):

    def __init__(self, serial={"baudrate": 19200, "com_port": "COM5"}, **kwargs):
        import serial as pyserial
        self._baudrate = serial["baudrate"]
        self._com_port = serial["com_port"]
        self.ser = pyserial.Serial(timeout=1)
        self._is_v2 = False
        super().__init__(**kwargs)

    @property
    def is_v2(self):
        return self._is_v2

    @is_v2.setter
    def is_v2(self, value):
        self._is_v2 = value
        self.scale_factor = 0.001 if value else 1.0
        self.offset = 60.00 if value else 0.00

    def do_open(self):
        import serial as pyserial
        from serial.tools import list_ports
        self.ser.baudrate = self._baudrate
        for port, desc, hwid in sorted(list_ports.comports()):
            if port == self._com_port:
                break
        else:
            print(f"Port {self._com_port} not found in list of comports.")
            return
        if not self.ser.is_open:
            self.ser.port = self._com_port
            try:
                self.ser.open()  # TODO: Add error handling.
                # Silence transmission temporarily
                self.ser.write("AXON-\r".encode())
                # Request version information.
                self.ser.write("V\r".encode())
                # readlines will capture until timeout
                pattern = "([0-9]+\.[0-9]+)"
                for line in self.ser.readlines():
                    match = re.search(pattern, line.decode("utf-8").strip())
                    if match is not None:
                        v = match.group()  # e.g., "2.20"
                        v_maj = int(v.split(".")[0])
                        self.is_v2 = v_maj >= 2
                        break
                # Resume transmission.
                self.ser.write("AXON+\r".encode())
                _ = self.ser.readline()  # Clear out the first response to AXON+
            except pyserial.serialutil.SerialException:
                print("Could not open serial port")

    def do_close(self):
        self.ser.close()

    def update(self):
        if self.ser.is_open:
            in_str = self.ser.readline().decode('utf-8').strip()
            if in_str:
                try:
                    raw_value = float(in_str) * (self.scale_factor or 1.0)
                    return raw_value

                except ValueError:
                    print("DDU result: {}".format(in_str))
        return None
