The documentation is hosted online at [https://sachslab.github.io/OpenMER/](https://sachslab.github.io/OpenMER/). Please navigate there for the latest version.

Dr. Adam Sachs is a neurosurgeon at the Ottawa Hospital where he and his team perform DBS surgery to treat motor disorders such as Parkinson's Disease, dystonia, and tremor. Part of the surgical procedure includes microelectrode recording (MER) to map the tissue around the intended DBS target to correct for intrinsic error in the DBS targeting process (i.e., due to imaging, planning, stereotaxy, and brain shift) and to refine the target location.

MER requires specialized equipment and software. While all-in-one medical devices are recommended, Dr. Sachs' research requires a more bespoke solution with multipurpose equipment and custom software. The software and some documentation are made available here with the goal of helping other clinician-scientists who wish to use custom systems for DBS MER.

## Equipment

Here is the list of equipment we use. It may be possible to use this software with other equipment.

* A variety of microelectrodes, but mostly [FHC Microtargeting Electrodes](https://www.fh-co.com/product-category/microtargeting/).
* We use the [Blackrock Neuroport](https://www.blackrockmicro.com/neuroscience-research-products/neural-data-acquisition-systems/neuroport-daq-system/) for signal acquisition, processing, and digitization. Other devices are possible via [labstreaminglayer](https://labstreaminglayer.readthedocs.io/).
* An [FHC Depth Digitizing Unit (DDU)](https://www.fh-co.com/product/microtargeting-controller-power-assist-system-2-0/) - they have similar units for the Nexdrive and STar Drive.
* A drive compatible with the DDU, such as the [Medtronic Nexdrive](https://www.medicalexpo.com/prod/medtronic/product-70691-503248.html) or the [FHC STar Drive](https://www.fh-co.com/product/star-drive-motor-encoder-system/)
* [Optional] A [Blackrock Cerestim](https://www.blackrockmicro.com/neuroscience-research-products/ephys-stimulation-systems/cerestim-96-neurostimulation-system/) for microstimulation.

## Software

OpenMER is a Suite of applications for visualizing signals in real-time:

![Image of vis apps](https://github.com/SachsLab/OpenMER/blob/master/vis_apps_screenshot.PNG?raw=true)

* *SweepGUI* - Plots continuous signals in sweeps, optional high-pass filter, and sonifies a channel.
* *RasterGUI* - Plots events (i.e., spikes) in a raster plot, with event rate displayed in the corner (up to 8 sec history)
* *WaveformGUI* - Plots the waveforms of the last N threshold crossing events.
* *DepthGUI* - Displays the depth readout from the drive (including optional offset), and sends that depth to other consumers.
  * sent to Blackrock NSP as a Comment;
  * pushed on a [labstreaminglayer](https://github.com/sccn/labstreaminglayer) outlet;
  * broadcast over ZeroMQ (see [ZeroMQ Port list](for-developers.md#interprocess-communication))
* *ProcedureGUI* - Sets patient and procedure info, and controls recording state.
  * The database interaction occurs via the ORM of a Django app called [SERF](https://github.com/cboulay/SERF) backed by a MySQL database.
  * Launching ProcedureGUI also launches two processes:
    * Segments_Process to capture raw segments at each depth and Features_Process to calculate features from those segments.
* *CommentGUI* (not shown) - Send comments to the Blackrock NSP, with some widgets specialized for kinesthetic mapping.

We also use a GUI application we developed called [*CereStimDBS*](https://github.com/CerebusOSS/CereStimDBS) for controlling the Blackrock CereStim96 in a convenient manner for DBS surgeries.

Please see [Getting Started](getting-started.md) documentation on how to set up OpenMER then look at the [Usage Instructions](usage-instructions.md) for simple OpenMER operating instructions.
