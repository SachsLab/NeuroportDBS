## Blackrock NSP

If Central is running then these tools should attempt to connect to Central's shared memory, and the network settings are irrelevant. If Central is not running then you'll have to make sure the network settings are correct, and this may depend on how your PC and NSP are connected.

The NSP always has the same ip address: 192.168.137.128. I don't think this can be changed, but if it is then you'll have to change that setting in the connect dialog window.

If the PC is linked directly to the NSP, then we use the following network adapter settings. In the adapter properties,  double click on Internet Protocol Version 4 (TCP/IPv4). Set the IP address to be 192.168.137.1 and the Subnet mask 255.255.255.0.  If you require a different IP address then you'll have to change this in the connect dialog window.

The client (PC) port defaults to 51002
The client IP address is 192.168.137.1 on Windows, and Mac and Linux use netmasks: 255.255.255.255 on Mac, and 192.168.137.255 on Linux
The NSP IP address is 192.168.137.128 and port 51001 

New digital NSPs (Gemini) have different settings and are not fully supported by OpenMER.

## DDU numbers changing too fast!

Version 2 of FHC's DDU returns the depths in um, but the DepthGUI software is expecting numbers in mm. The DDU version should be automatically detected now. If you are still experiencing this issue then update OpenMER.
