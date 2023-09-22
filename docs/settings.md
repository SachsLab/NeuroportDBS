## Settings Format

Our settings use the QSettings ini format.

## Modifying Settings

The default settings are contained in files located within the open_mer Python package.

The user must copy these files into their home directory then modify them there.
Copy all .ini files from `<distribution>\<python>\<python-3.x.x.y>\Lib\site-packages\open_mer\resources\settings` to %HOME%\.open_mer\.
This can be done by running `python -m open_mer.scripts.ResetUserSettings`.

> Warning: The ResetUserSettings script will wipe out any previously modified settings in the user's home directory.

Settings in the home directory will take precedence over the settings in the open_mer package.

### CbSdkConnection.ini

If the OpenMER GUI ini files have `class=CerebusDataSource` in their `[data-source]` section,
then the CbSdkConnection.ini will be used to determine how to connect to the Cerebus (Blackrock Neuroport) data source.

By default, every line is commented out and the cerebus.cbpy default settings are used. The default settings will
first attempt to use the shared memory created by Central, then attempt to connect directly to a legacy NSP located at 
192.168.137.128 using port 51001.

If neither is true (not on the same PC as Central, or not directly connected to legacy NSP), then modify the settings.

* `client-addr=192.168.137.1`
  * Set this to the IP address of the PC running OpenMER.
  * Use `192.168.137.1` for the Blackrock Host PC.
* `client-port=51002`
  * Set this to the port used to transmit control packets to the NSP. It is unlikely this will ever change from 51002.
* `inst-addr=192.168.137.128`
  * Set this to the IP address of the NSP (or the PC running nPlayServer in bcast mode).
  * Use `192.168.137.128` for legacy NSP
  * Use `192.168.137.200` for digital Neuroport system (Gemini Hub)
* `inst-port=51001`
  * Use `51001` for legacy NSP and `51002` for digital Neuroport system.
* `receive-buffer-size=8388608`

### Style.ini

Contains generic style settings that are expected to be consistent across applications,
such as MainWindow framing and line colors.

Settings in Style.ini may be overwritten by settings in GUI-specific ini files.

### DepthGUI.ini

### FeaturesGUI.ini

### MappingGUI.ini

### ProcessGUI.ini

### RasterGUI.ini

### SweepGUI.ini

### WaveformGUI.ini
