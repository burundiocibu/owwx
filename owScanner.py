#!/usr/bin/env python

import ow, datetime, time, sys, numpy
import string
import tables
import matplotlib,pylab

import OwConfig, OwLib

def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-d", "--debug",
                      dest="debug", default=0, action="count",
                      help="Increase the debug level")

    (options, args) = parser.parse_args()

    sensor_list = OwConfig.sensor_list

    OwConfig.debug = options.debug
    if options.debug:
        print "Debug: %d" % options.debug
        print "Connecting to: %s" % OwConfig.owserver

    # initialize the interface and set the desired units.
    ow.init(OwConfig.owserver)
    if ow._OW.get('/settings/units/temperature_scale')=='C':
        ow._OW.put('/settings/units/temperature_scale', 'F')
 
    # See which sensors are actually present on the net and report the missing
    print "Searching bus for sensors"
    t0 = time.time()
    OwLib.find_sensors(ow.Sensor('/'), sensor_list, options.debug)
    dt = time.time() - t0
    if options.debug:
        print "\ndt=%.2f"%dt
    missing = [n for n,s in sensor_list.items() if 
               not 'sensor' in s.keys() and 
               not s['ignore'] and 
               not 'sources' in s.keys()]

    if len(missing):
        print "Failed to find %d sensors" % len(missing)
        print missing
    else:
        print "Found all sensors"
    if options.debug>2:
        import pprint
        pp = pprint.PrettyPrinter(indent=3)
        pp.pprint(sensor_list)

    print "time,",
    for name,sensor in sensor_list.items():
        if not 'sensor' in sensor.keys():
            continue
        print "%5s,"%(name),
    print

    while True:
        print "%s,"%time.strftime("%m/%d/%y %H:%M:%S"),
        for name,sensor in sensor_list.items():
            if not 'sensor' in sensor.keys():
                continue
            value = OwLib.read_sensor(sensor['sensor'])
            if value == None: 
                print "None ,",
            else:
                print "%5.2f,"%value,
        print
    # end of infinite loop

    return
# end of main()

if __name__ == "__main__":
    main()
