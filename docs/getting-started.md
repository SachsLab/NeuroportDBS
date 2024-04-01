The PC that runs our software is directly connected to the acquisition system, but it is never connected to the internet. Thus, we create a portable install on a thumb drive which we then copy to the clinical PC.

> For development or testing on an internet-connected computer, or a non-Windows computer, please look at the [For Developers](for-developers.md) documentation.

## Installation

### Distribution

Copy the `<distribution>` folder from the thumb drive to the instrument PC.

> Be sure to choose a destination with lots of disk space because many recording segments will be stored within the database located in this folder.

> If you do not have the `<distribution>` folder then follow the [Preparing Distribution](preparing-distribution.md) instructions to create it.

### Configure

The `<distribution>` folder is ready to use as-is. However, with some additional steps it can be more useful on the target PC.

#### Shortcuts

* Make a desktop shortcut to `<distribution>\mysql\bin\mysqld.exe`.
* Make a desktop shortcut to `<distribution>\<python>\scripts\OpenMER.bat`

#### Settings files

OpenMER functionality can be modified via INI files. See [Settings](settings.md) for more information.

## Using OpenMER

See [Usage Instructions](usage-instructions.md)
