owwx
====

This is a bit of python programming to collect data from a set of [owservers](http://owfs.org) and store it in a local hdf5 database.
The 1-wire devices that are tracked by the device ID, not by location in the 1-wire network. This allows devices to
be moved around on the network withouth having to recode the paths to the devices.

Its really a personal project but I put it on GitHub for any to use.

Python dependancies:
   numpy, tables, owpython (from owfs)
   

OwLib.py: routines for finding the location of all the devices on the various owservers.
OwConfig.py: The configuration of a specific set of devices that should be found.
owTree: lists all the devices found on a specific owserver instance
owScanBuss: 
