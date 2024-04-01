* Run the MySQL daemon
  * Win: `mysqld` (create a shortcut) 
  * macOS: `brew services start mysql`
* Run OpenMER Suite
  * Win: Use the batch file
  * macOS: No batch file yet.

Additional details follow.

## Configure Neural Data Source

### Blackrock NSP

* The NSP must be on.
  * Can use nPlayServer instead for testing. See the [relevant section in the developer docs](for-developers.md#nplayserver).
* Central should be running first if OpenMER and Central are on the same PC.

### LSL Source

It is also possible to use an LSL outlet as a data source.
Documentation for this feature is currently unavailable.

## Raw data visualization

SweepGUI -- RasterGUI -- WaveformGUI

No special instructions. These should work as long as a recognized data source is available and transmitting data.

Check out the relevant sections in the [settings docs](settings.md).

### Sweep Plot Audio

The SweepGUI has the ability to stream one of the visualized channels out over the computer's speaker system. You can select which channel is being streamed either by clicking on one of the radio buttons near the top or by using a number on the keyboard (0 for silence, 1-N for each visualized channel). Additionally, you may use left-arrow and right-arrow for cycling through the channels, and Spacebar selects silence.

We map a USB footpedal to right-arrow so the channels can be cycled without using our hands.

## Depth

It is very important to modify the [DepthGUI settings](settings.md#depthguiini) to set the source of the depth information. 

* Enter your distance to target
* If, like us, the depth readout isn't the same as your distance to target, then add an offset.
  * It defaults to -60 mm if it detects that the DDU is the version most commonly associated with the StarDrive.

## Procedure

* Under the Subject tab:
    * Type a patient Id or select from the drop-down list if resuming a previously-stored patient.
    * Enter the remaining information.
* Under the Procedure tab:
    * Target name (e.g. STN, GPi, Vim)
    * Type: DBS
    * Recording configuration: choose one that matches best.
    * Electrode configuration: This refers to the arrangement of the electrodes in the BenGun when using an array. Choose the one that matches best.
    * Enter Entry and Target coordinates. Also enter Distance to target to confirm.
    * If you record the Nexframe orientation by recordings its A and E locations then enter them here.
      * TODO: use perfectly-aligned values as defaults.
    * If you use an offset adapter you can specify the direction (A to H) and the offset size in mm.
        
* Click OK to start the GUI

## Features

* Click on the "Record" button.
    * Note: To change the default recording path, edit `WPy64-3850\python-3.8.5.amd64\Lib\site-packages\neuroport_dbs\settings\defaults.py` and change the `BASEPATH` value. (We hope to make this easier via a config file in the future.)
* After a new depth is entered and the depth remains constant for 4-8 seconds (depending on signal quality), a segment will be added to the database.
* The current trajectory that is visualized is by default synchronized with the Sweep GUI selection for audio. To change which trajectory is being visualized, you can change which channel you are listening to in SweepGUI, or uncheck the synchronize box and set the channel manually.
