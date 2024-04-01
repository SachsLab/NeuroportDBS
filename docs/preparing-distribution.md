The target PC is usually a clinical device that is not internet connected. Thus, we prepare a distribution to be copied onto a thumb drive then copied to the target PC.

After completing these instructions to prepare the distribution, head back to [Getting Started](./getting-started.md) for further instructions.

## Base

Create a folder somewhere you have write access. The location should have at least 2 GB disk space. Name the folder whatever you like. Throughout this documentation, we refer to the folder as `OpenMER_Suite`.

## Python

* Download the latest [WinPython release](https://winpython.github.io/#releases).
  * Get the one ending in `dot` as this excludes some unnecessary bloat.
  * These instructions were tested with WinPython64-3.11.4.0dot
* Run the WinPython self-extracting executable and choose the `OpenMER_Suite` folder as the extraction location. This will create a `OpenMER_Suite/<winpython>` folder containing a full Python distribution with many useful packages installed.
  * The full list of installed packages can be found [here](https://github.com/winpython/winpython/blob/master/changelogs/).
* [Edit the `<winpython>\settings\winpython.ini` file](https://sourceforge.net/p/winpython/wiki/Environment/) and add the following line: `PATH = %WINPYDIR%\Lib\site-packages\PyQt5\Qt\bin;%PATH%`
  * TODO: Is this still necessary with PySide6?
* In the WinPython folder, run "WinPython Command Prompt". This will open a Command Prompt with all the paths configured to use this new Python distribution.
  * Confirm with `echo %PATH%`. There should be many paths in the WinPython tree.
* Uninstall PyQt5 (we will be installing PySide6): `pip uninstall pyqt5`
  * TODO: Maybe no longer necessary with the `dot` WinPython?
* Install all the Python packages according to the [Required Python Packages](#required-python-packages) section below.
* Make a batch file `OpenMER_Suite\<winpython>\Scripts\OpenMER.bat` with the following contents:
    ```shell script
    @echo off
    call "%~dp0env_for_icons.bat"
    start "" "%WINPYDIR%\Scripts\dbs-meracquire.exe" /command:%1 /B
    start "" "%WINPYDIR%\Scripts\dbs-procfeatures.exe" /command:%1 /B
    start "" "%WINPYDIR%\Scripts\dbs-sweep.exe" /command:%1 /B
    start "" "%WINPYDIR%\Scripts\dbs-raster.exe" /command:%1 /B
    start "" "%WINPYDIR%\Scripts\dbs-waveform.exe" /command:%1 /B
    start "" "%WINPYDIR%\Scripts\dbs-ddu.exe" /command:%1 /B
    start "" "%WINPYDIR%\Scripts\dbs-procedure.exe" /command:%1 /B
    start "" "%WINPYDIR%\Scripts\dbs-features.exe" /command:%1 /B
    ```
  
> Note: Check OpenMER/setup.cfg `[options.entry_points]` for the correct names of the exe files.

### Required Python Packages

In your WinPython Command Prompt, try the following commands first. If they fail, download the wheels matching the version in the table and install the wheels directly.

> A great place to find wheels for Windows is http://www.lfd.uci.edu/~gohlke/pythonlibs/. The second best place to find wheels is in pypi.org and clicking on the "Download files" button for a particular package.

> Developers only: For each of the SachsLab packages (mspacman, cerebuswrapper, serf, **neuroport_dbs**), you have the option of cloning the repo then installing the package in-place for easier editing. Using the WinPython command prompt, run `pip install -e .` from within the cloned directory.

```
python.exe -m pip install --upgrade pip
# macOS developers: use `mamba` instead of `pip` for the next 1 line only.
pip install Django quantities numpy scipy Cython pyFFTW mysqlclient
pip install pylsl pyaudio PySide6 qtpy pyzmq pyqtgraph pyserial
pip install git+https://github.com/NeuralEnsemble/python-neo.git
pip install git+https://github.com/SachsLab/pytf.git
pip install git+https://github.com/SachsLab/mspacman.git
# macOS developers: comment out the following line and uncomment the subsequent line
pip install https://github.com/CerebusOSS/CereLink/releases/download/v7.6.4/cerebus-0.4-cp311-cp311-win_amd64.whl
# pip install https://github.com/CerebusOSS/CereLink/releases/download/v7.6.4/cerebus-0.4-cp311-cp311-macosx_11_0_arm64.whl
pip install git+https://github.com/CerebusOSS/cerebuswrapper.git
pip install git+https://github.com/cboulay/SERF.git#subdirectory=python
pip install git+https://github.com/SachsLab/OpenMER.git
```

| Package        | Version          | Wheel                                                                                                           | pip command                                                                                                         |
|----------------|------------------|-----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| pySide6        | 6.5.2            |                                                                                                                 |                                                                                                                     |
| qtpy           | 2.4.0            |                                                                                                                 | https://github.com/spyder-ide/qtpy.git                                                                              |
| pyFFTW         | 0.13.1           |                                                                                                                 |                                                                                                                     |
| mysqlclient    | 2.2.0            |                                                                                                                 |                                                                                                                     |
| Django         | 4.2.5            |                                                                                                                 |                                                                                                                     |
| quantities     | 0.14.1           |                                                                                                                 |                                                                                                                     |
| python-neo     | git tag 340b0221 |                                                                                                                 | `pip install git+https://github.com/NeuralEnsemble/python-neo.git`                                                  |
| pylsl          | 1.16.1           |                                                                                                                 | `pip install pylsl`                                                                                                 |
| pytf           | 0.1              | [Link](https://github.com/SachsLab/pytf/releases/download/v0.1/pytf-0.1-py2.py3-none-any.whl)                   | `pip install git+https://github.com/SachsLab/pytf.git`                                                              |
| mspacman       | 0.1              | [Link](https://github.com/SachsLab/mspacman/releases/download/v0.1/mspacman-0.1-py2.py3-none-any.whl)           | `pip install git+https://github.com/SachsLab/mspacman.git`                                                          |
| cerebus        | 0.4              |                                                                                                                 | `pip install https://github.com/CerebusOSS/CereLink/releases/download/v7.6.4/cerebus-0.4-cp311-cp311-win_amd64.whl` |
| cerebuswrapper | 0.1              | [Link](https://github.com/SachsLab/cerebuswrapper/releases/download/v0.1/cerebuswrapper-0.1.0-py3-none-any.whl) | `pip install git+https://github.com/CerebusOSS/cerebuswrapper.git`                                                  |
| serf           | 1.2              |                                                                                                                 | `pip install git+https://github.com/cboulay/SERF.git#subdirectory=python`                                           |
| open_mer       | *                | [Link](https://github.com/SachsLab/NeuroportDBS/releases/download/)                                             | `pip install git+https://github.com/SachsLab/OpenMER.git`                                                           |

## MySQL

* Download [MySQL Windows ZIP Archive](https://dev.mysql.com/downloads/mysql/)
  * Tested with mysql-8.1.0-win64.zip
  * Don't choose the .msi
  * After selecting the zip, on the following page look for the "No thanks, just start my download" link.
* Extract the mysql zip into `OpenMER_Suite` and rename the extracted folder to `mysql`
* In the command prompt, `cd` into the `bin` subfolder of the unzipped mysql folder.
* Create a mysql\data folder along with the base databases: `mysqld --initialize-insecure --console`
  * You can change the default data directory, username, and password. See the section below on [Configuring MySQL Database Server](#configuring-mysql-database-server)
* Run `mysqld` in the `mysql\bin` folder. (Windows: `start /B mysqld.exe`; allow network access if asked.)
* Back in the command prompt, run `mysqladmin --user=root create serf`

* Install the serf databases with the following commands (available after serf Python package is installed):
    ```
    serf-makemigrations
    serf-migrate
    ```

### Configuring MySQL Database Server

* If you wish to use a different datadir then you must first create a `my.cnf` file in the root `mysql` folder with the following contents (commented out lines aren't necessary, just keeping them here for reference):
    ```
    [mysqld]
    datadir=path/to/data
    #port = 3306
    #socket = /tmp/mysql.sock
    #pid-file = /Volumes/STORE/eerfdata/Chadwicks-MacBook-Pro.local.pid
    #default-storage-engine = MyISAM
    #default_tmp_storage_engine = MyISAM
    #query_cache_type = 1
    #key_buffer_size = 2G
    #query_cache_limit = 400M
    ```
* If you wish to secure the database then you'll need to give the root account a password. Do so with `mysql_secure_installation`.
* If you change from the default username (`root`) and password (none) then you will have to tell `serf` what the username and password are. Create a file named `my_serf.cnf` and put it in the path identified by the following command: `python -c "import os; print(os.path.expanduser('~'))"` The file contents should be
    ```
    [client]
    user = root
    password = <new password>
    #port = 3306
    #socket = /tmp/mysql.sock
    ```