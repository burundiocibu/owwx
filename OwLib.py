#!/usr/bin/python

import ow, time, sys, numpy, solar, datetime

debug=0

class TimeValueHistory(object):
    """Used to maintain a history of values for an indicated length of time"""

    def __init__(self,depth):
        self.depth=depth  # how many obs to keep
        self.values = []
        self.times = []
        
    def add(self, value):
        """ Add a value to the history """
        t = time.time()
        self.values.insert(0, value)
        self.times.insert(0, t)
        if len(self.values) > self.depth:
            self.values.pop()
            self.times.pop()


import tables
class H5Obs(tables.IsDescription): 
    time = tables.Float64Col(dflt=0, pos = 1)
    val  = tables.Float32Col(dflt=-9999, pos = 1)

def apply_correction(v, label):
    """Compute the correction for the value v, taken from the sensor label"""
    from OwConfig import ct
    mb = ct.get(label,[1,0])
    if debug>2:
        print ", value=", v, ", mb =", mb, v-(v*mb[0] + mb[1])
    return v*mb[0] + mb[1]


def read_sensor(s):
    """Read a single sensor and dress up the results in engineering units. This
    routine will return None when it has any problems. This routine will also apply any correction to
    the reading as encoded in the sensor_list."""
    from ow import exUnknownSensor
    from OwConfig import owlabels
    v=None

    try:
        label = owlabels[s.address]
        if debug>2: print "Reading", label,

        if   label[0:1] == 'T':  v = 32.0 + float(s.temperature)*9./5.
        elif label[0:2] == 'P1': v = 0.6753 * float(s.VAD) + 26.6531 # mm Hg
        elif label[0:2] == 'RG': v = int(s.counters_B)/100.0 - 1.02 # offset as off 5/8/10
        elif label[0:2] == 'WS': v = int(s.counters_A) # counts
        elif label[0:2] == 'LC': v = int(s.counters_A) # counts
        elif label[0:2] == 'LS': v = 1.0e6*float(s.vis)/390.0 # uA
        elif label[0:3] == 'WH1': v = compute_bin(s.volt_ALL)
        elif label[0:3] == 'WH2': v = compute_rfc4000(s.volt_A)
        elif label[0:2] == 'RH': v = float(s.humidity) # % relative humidity
        elif label[0:6] == 'RH4021':
            # This is the formula for a HIH4021 device
            Vo=float(s.VAD)
            Vs=float(s.VDD)
            T=5.0/9.0*(float(s.temperature)-32.0)
            RHu = 161.29 * (Vo/Vs - 0.16)
            RHc = RHu / (1.0546 - 0.00216*T)
            print "Vo=%4.2f, Vs=%4.2f, T=%5.2f, RHc=%5.2f, RHu=%5.2f s.humidity=%5.2f"%(
                Vo,Vs,T,RHc,RHu,float(s.humidity))
            v = RHc
        else:
            print "Unknown type:", type,
        if v:
            v = apply_correction(v, label)

    except ValueError:
        if debug>2:print
        print "Caught ValueError exception on",label

    except exUnknownSensor:
        if debug>2:print
        print "Caught unknown sensor exception on", s

    return v
#

def update_all_sensors(sensor_list):
    for name,sensor in sensor_list.items():
        update_sensor(sensor)


def update_sensor(sensor):
    """Update a single sensor in the OwConfig.sensor_list list"""
    if not 'sensor' in sensor.keys():
        return
    t0 = time.time()
    if len(sensor['tv'].times):
        dt = t0 - sensor['tv'].times[0]
        if dt < sensor['rate']:
            return

    value = read_sensor(sensor['sensor'])

    if value != None:
        sensor['tv'].add(value)
        if debug>2:
            dt = sensor['tv'].times[0] - t0
            last = sensor['tv'].values[0]
            n = len(sensor['tv'].values)
            print "%s %-10s:%.2f n=%d(%.2f sec)"%(
                time.strftime("%H:%M:%S"), sensor['name'],
                last, n, dt)
    else:
        if debug:
            print "%s No value for %-10s"%(
                time.strftime("%H:%M:%S"), sensor['name'])

    return
# end of update_sensor()



def print_values(sensor_list):
    """Prints all current values to stdout"""

    print time.strftime("%m/%d/%y %H:%M:%S")
    for name,sensor in sensor_list.items():
        if sensor['value'] != None:
            print "  %-14s" % (name+": "),
            value = sensor['value']
            print "  ",sensor['fmt']%sensor['value']
    sys.stdout.flush()
    return
# end of print_values()


def find_all_sensors():
    if debug: print "Scanning 1wire buss..."
    t0 = time.time()
    all_sensors={}
    find_sensors(all_sensors)
    dt = time.time() - t0
    if debug: print "Scan took %.2f secons"%dt
    return all_sensors
# end of find_all_sensors()


def find_sensors(slist, sensor=None):
    """ Walk the entire sensor tree, fill in the full path to each
    sensor that is found"""
    from OwConfig import owlabels

    if not sensor: sensor = ow.Sensor('/')

    for next in sensor.sensors():
        if next._type in [ 'DS2409', ]:
            if debug==1: sys.stdout.write("+"); sys.stdout.flush()
            elif debug>1: print next._path, next.type
            find_sensors(slist, next)
        else:
            if debug==1: sys.stdout.write("."); sys.stdout.flush()
            elif debug>1: print next._path, next.type, owlabels.get(next.address,"")
            slist[next.address] = next

    return
# end of find_sensors()


def compute_obs(sensor_list):
    """Computes observations from the sensor readings. This also fills in
    those sensors that don't have an associated physical device."""

    for name,sensor in sensor_list.items():
        if 'src' in sensor.keys():
            src = sensor_list[sensor['src']]['tv']
        else:
            src = sensor['tv']

        if len(src.values) == 0:
            continue

        values = numpy.array(src.values)
        times = numpy.array(src.times)

        label = sensor['label']
        if debug>1:
            print "computing",label

        if label[0:2] == 'WS':
            if len(times)<10: continue
            t0 = times[0]
            for n in xrange(1,len(times)):
                if t0 - times[n] > 2*60:
                    break
            if debug>1:
                print sensor['name'],"n=%d"%n
            dr = values[:-1] - values[1:]
            dt = times[:-1] - times[1:]
            s = 2.5 * dr / dt
            value = sum(s[0:n])/n

        elif label[0:2] == 'WG':
            if len(times)<2: continue
            t0 = times[0]
            for n in xrange(1,len(times)):
                if t0 - times[n] > 10*60:
                    break
            if debug>1:
                print sensor['name'],"n=%d"%n
            dr = values[:-1] - values[1:]
            dt = times[:-1] - times[1:]
            s = 2.5 * dr / dt
            value = max(s[0:n])

        elif label[0:2] == 'WH':
            if len(times) < 5: continue
            t0 = times[0]
            for n in xrange(1,len(times)):
                if t0 - times[n] > 5*60:
                    break
            if debug>1:
                print sensor['name'],"n=%d"%n
            v = values[0:n]
	    if debug>1:
               print v
            value = values.mean() # cav(v)

        else:
            value = values[0]
            t = times[0]
            if len(values)>2:
                lim = sensor.get('lim',20)
                med = numpy.median(values)
                _mad = mad(values)
                #lim = max(devlim*mad, abs(0.2 * med))
                for i in range(values.size):
                    if abs(values[i] - med) > lim:
                        continue
                    value = values[i]
                    t  = times[i]
                    break
                if i != 0 and debug:
                    print "%s %-10s: "%(
                        time.strftime("%H:%M:%S", time.localtime(times[0])),
                        sensor['name']),
                    print "excess: [",
                    for j in range(i): print "%5.2f"%(abs(values[i] - med) - lim),
                    print "] med: %5.2f mad: %5.2f lim: %5.2f"%(med, _mad, lim)

        sensor['value'] = value
        sensor['time']  = t
        if debug>1:
            print "%s %-10s:%.2f"%(
                time.strftime("%H:%M:%S", time.localtime(t)),
                sensor['name'], value),
            print values

    return
# end of compute_obs()


def qv(v):
    """ Quantize a voltage 0-5 into values 0,1,2"""
    vf = float(v)
    if vf < 5*1/4:
        return '0'
    elif vf < 5*3/4:
        return '1'
    else:
        return '2'
# end of qv()


def compute_bin(volt_ALL):
    """ Convert the voltages from a wind sensor to the bin"""
    v2b={
        '2212':0,
        '2112':1,
        '2122':2,
        '1122':3,
        '1222':4,
        '1220':5,
        '2220':6,
        '2200':7,
        '2202':8,
        '2002':9,
        '2022':10,
        '0022':11,
        '0222':12,
        '0221':13,
        '2221':14,
        '2211':15,
        }

    s = "".join([qv(float(v)) for v in volt_ALL.split(',')])
    if v2b.has_key(s):
        return v2b[s]
    if debug:
        print "invalid bin", volt_ALL, s
    return None
# end of compute_bin


def compute_heading(volt_ALL):
    """ Convert the voltages from a wind sensor to heading."""
    b = OwLib.compute_bin(volt_ALL)
    return b * 22.5
# end of compute_heading


def compute_rfc4000(v):
    """Convert the voltage observed from a rfc4000 rotary sensor into degrees"""
    # These are the voltages as the devices crosses from 0 to 360
    v_min = 0.131 # V
    v_max = 4.403 # V
    v = float(v)
    d = 360.0 * (v-v_min)/(v_max - v_min)
    if d>=360 or d<0: d=0
    return d


d2h={
    0:'N',
    22.5:'NNE',
    45:'NE',
    67.5:'ENE',
    90:'E',
    112.5:'ESE',
    135:'SE',
    157.5:'SSE',
    180:'S',
    202.5:'SSW',
    225:'SW',
    247.5:'WSW',
    270:'W',
    292.5:'WNW',
    315:'NW',
    337.5:'NNW',
    -1:'err'
    }

def mad(v):
    """Compute the median absolute deviation of the given array"""
    if len(v)<2:
        return 0

    xd = abs(v - numpy.median(v))
    return numpy.median(xd)/0.6745
#

from math import exp, log

def wvpp(t, rh):
    t = (t - 32) * 5 / 9 # convert temperature to celsius
    es = 6.112 * exp(17.67*t/(t+243.5))
    e = es * rh / 100    
    return e


def dewpoint(t, rh):
    """ temp in degrees F, rh in percent
    returns dewpoint in degrees F
    http://en.wikipedia.org/wiki/Dew_point
    """
    e = wvpp(t,rh)
    e=e/6.112
    td = 243.5*log(e)/(17.67-log(e))
    td = td * 9/5 + 32
    return td

def smoothPlot(ax, x, y, fmt=".", label="", color="", window_len=0):
    if x.ndim != 1 or y.ndim !=1:
        raise ValueError, "Only accepts rank 1 arrays."

    if x.size<2 or y.size<2:
        return

    n = int(window_len)
    if n>3 and n<y.size:
        s=numpy.r_[2*y[0]-y[n:1:-1],y,2*y[-1]-y[-1:-n:-1]]
        w=eval('numpy.bartlett(n)')
        y=numpy.convolve(w/w.sum(),s,mode='same')
        y=y[n-1:-n+1]
        y=y[n-1:-n+1]
        x=x[n-1:-n+1]

        ax.plot_date(x, y, fmt=fmt, label=label, markersize=2)
#

def cav(v):
    """Compute a consensus average of the data in v"""
    N = 16
    # The number of bins in the data

    bins = numpy.zeros(N,dtype=int)
    for c in v:
    	if c:
            bins[c%N] += 1

    sums = numpy.zeros(N,dtype=int)
    for i in range(N):
        for j in range(5):
            sums[i] += bins[(i+j)%N]

    s = sums.max()
    if s==0:
        return 0

    m = sums.argmax()
    w=0
    for i in range(1,5):
        w += i * bins[(m+i)%N]

    w = w * 45.0 / s
    d = (m * 45.0 + w)%720
    return d/2
# end of consensus average


def solar_radiation(utc_datetime):
    """Returns maximum solar radiation at the indicated time"""
    lon=-97.71623
    lat=30.43216
    el=solar.GetAltitude(lat,lon,utc_datetime)
    r=solar.radiation.GetRadiationDirect(utc_datetime,el)
    return r


if __name__ == "__main__":
    from sys import argv
    t = float(argv[1])
    rh = float(argv[2])
    print "t=%.2f F, rh=%.1f %%"%(t,rh)
    print "dewpoint=%.2f F"%dewpoint(t,rh)

