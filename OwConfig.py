#!/usr/bin/python

h5_file = "/home/littlej/wx/ow.h5"
log_file = "/home/littlej/wx/wx.log"
png_dir = "/var/www/wx"
log_rate = 60 # rate in seconds

debug=0

import OwLib

location=(-97.71623, 30.43216, 800) # lon, lat, ht(ft)

# Each 1 wire device gets a label. This translates addresses to the 
# assigned label. The lable is used to determine how to compute the reading from the device
owlabels={
    '28406F31000000D2':'T0',
    '28BC7D3100000022':'T1',
    '289E9E310000006E':'T2',
    '28A5A7310000000C':'T3',
    '28E58F31000000BF':'T4',
    '28309E3100000021':'T6',
    '28725D3100000056':'T7',
    '285F5C3100000067':'T9',
    '289D9A3100000028':'T11',
    '282E963100000057':'T12',
    '28C48A31000000EC':'T13',
    '284171310000003B':'T14',
    '28026431000000B9':'T15',
    '28B89831000000F6':'T16',
    '28A86B3100000045':'T17',
    '28C57D310000002C':'T18',
    '28349A31000000E2':'T19',
    '28867A3100000051':'T20',
    '287887310000007A':'T21',
    '268E3E1500000007':'RH1',
    '2649491500000021':'RH2',
    '1D2AEA090000004E':'RG1',
    '26DDF8AE000000CB':'P1',
    '1D4CEA090000003F':'WS2',
    '262161E7000000F3':'LS1',
    '10B2CDED01080055':'T22',
    '10F2A1ED01080010':'T23',
    '264058E700000070':'RH3',
    '1051DAED01080008':'T24',
    '261D6CE70000008F':'RH4',
    '20891C0E000000DB':'WH2',
    '1000DFED010800C3':'T25',
    '1003F2ED0108008E':'T26',
    '10F2F2ED010800CB':'T27',
    '0000000000000000':'derived' # dummy label for sensors that are computed
    }

# This just makes the reverse map to translate from a label to address
owaddrs = {}
for (k,v) in owlabels.iteritems():
    owaddrs[v] = k


from numpy import array,matrix
from numpy.linalg import solve

corrections={'T2':0, 'T6':-0.11, 'T15':0.30,'RH2':-10}
 # ct: calibration table. for each sensor. The corrected value is o*ct[0] + ct[1] 
# When a two point calibration is performed, this is converted to the above 
# coefficients using the linalg.solve routine which solves the equation
# b = Ax
# b is the array of expected values at the calibration points
# A has the observed values at the calibration points in the first column and
# ones in the second column
ct={
    'T6' :array([1,0]),
    'T15':array([1,-0.30]),
    #                    meas1   1   meas2  1           exp1 exp2
    'RH2':solve(matrix([[10.8,   1], [83.5,  1]]), array([0,   75.3])), # Sep 2009
    'RH1':solve(matrix([[1,      1], [72.3,  1]]), array([0,   75.3])), # Nov 12 2009
    'RH3':solve(matrix([[-0.7,   1], [62.6,  1]]), array([0,   75.3])), # Nov 12 2009
    'RH4':solve(matrix([[0.3,    1], [62.0,  1]]), array([0,   75.3])), # Nov 12 2009
    'RH3':solve(matrix([[-2.3,   1], [66.6,  1]]), array([0,   75.3])), # Nov 07 2010
    'RH4':solve(matrix([[-2.3,   1], [64.8,  1]]), array([0,   75.3])), # Nov 07 2010
    'RH4':solve(matrix([[-2.3,   1], [66.8,  1]]), array([0,   75.3])), # Nov 07 2010
    }

# This is a list of devices that are 'in-use' on the network.
# Note that the rate corresponds to how often the sensor will be sampled. Values
# will be stored in the database every log_rate seconds. Depth is the number of
# samples to keep in a local buffer. This needs to be greater than 2 if the
# outlier detection is to work.
# setting a member called 'ignore' will cause that sensor to be ignored - useful
# for temporaryly disabling a sensor (i.e. for calibration)
sensor_list = {
    'RainAcc':{
        'label':'RG1', 'rate':60, 'depth':5, 
        'name':'total rainfall',
        'color':'blue', 'fmt':'%6.2lf', 'units':'in',
        'ignore':False},

    'Wspeed':{
        'label':'WS2', 'rate':10, 'depth':60,
        'name':'wind speed', 'linewidth':0,
        'smoothing': 3, # as a percentage of the length of data plotted
        'color':'salmon', 'fmt':'%6.2lf', 'units':'mph', 'marker':'+-',
        'ignore':False},

    'Wgust':{
        'label':'WG2', 'src':'Wspeed', 'rate':60, 'depth':1,
        'name':'wind gust', 'linewidth':0,
        'color':'deeppink', 'fmt':'%6.2lf', 'units':'mph', 'marker':'x-',
        'ignore':False},

    'Whead':{
        'label':'WH2', 'rate':15, 'depth':20,
        'name':'wind heading', "linewidth":0,# 'smoothing':2,
        'color':'blue', 'fmt':'%6.0lf', 'units':'deg', 'marker':'x-',
        'ignore':False},

    'Pambient':{
        'label':'P1', 'rate':60, 'depth':10, 
        'name':'baro pressure',
        'color':'blue', 'fmt':'%6.2lf', 'units':'inHg',
        'ignore':False},

    'Hthermostat':{
        'label':'RH1', 'rate':60, 'depth':10, 
        'name':'living room humidity',
        'color':'blue', 'fmt':'%6.2lf', 'units':'%RH',
        'ignore':False},

    'Hout':{
        'label':'RH3', 'rate':60, 'depth':10, 
        'name':'outside humidity',
        'color':'green', 'fmt':'%6.2lf', 'units':'%RH',
        'ignore':False},

    'Toutside':{
        'label':'T23', 'rate':60, 'depth':10, 
        'name':'outside temp',
        'color':'chocolate', 'fmt':'%6.2lf', 'units':'F',
        'ignore':False},

    'Tonepi':{
        'label':'T9', 'rate':60, 'depth':10, 
        'name':'onepi system temp',
        'color':'chocolate', 'fmt':'%6.2lf', 'units':'F',
        'ignore':False},

    'Tgame':{
        'label':'T3', 'rate':60, 'depth':10, 
        'name':'game room temp',
        'color':'chocolate', 'fmt':'%6.2lf', 'units':'F',
        'ignore':False},


    # The following are 'derived' sensors. that means they are computed
    # from readings that are stored in the database
    'Tdthermostat':{
        'label':'derived',
        'name':'living room dewpoint',
        'sources':('dewpoint', 'Tthermostat', 'Hthermostat'),
        'color':'lightblue', 'fmt':'%6.2lf', 'units':'F',
        'ignore':False},

    'Tdoutside':{
        'label':'derived',
        'name':'outside dewpoint',
        'sources':('dewpoint', 'Toutside', 'Hout'),
        'color':'lightgreen', 'fmt':'%6.2lf', 'units':'F',
        'ignore':False},

    'WVinside':{
        'label':'derived',
        'name':'inside water vapor partial pressue',
        'sources':('wvpp', 'Tthermostat', 'Hthermostat'),
        'color':'darkblue', 'fmt':'%6.2lf', 'units':'hPa',
        'ignore':False},

    'WVoutside':{
        'label':'derived',
        'name':'outside water vapor partial pressue',
        'sources':('wvpp', 'Toutside', 'Hout'),
        'color':'darkgreen', 'fmt':'%6.2lf', 'units':'hPa',
        'ignore':False},

    'RainHour':{
        'label':'derived',
        'name':'Rainfall over the last hour',
        'sources':('rainhour', 'RainAcc',),
        'color':'darkgreen', 'fmt':'%6.2lf', 'units':'in',
        'ignore':False},

    'RainDay':{
        'label':'derived',
        'name':'Rainfall since the midnight local',
        'sources':('rainday', 'RainAcc',),
        'color':'darkgreen', 'fmt':'%6.2lf', 'units':'in',
        'ignore':False},

    'RainDay':{
        'label':'derived',
        'name':'Rainfall since Jan 1 of current year',
        'sources':('rainyear', 'RainAcc',),
        'color':'darkgreen', 'fmt':'%6.2lf', 'units':'in',
        'ignore':False},
}


station_list = [
    "KATT", "KAUS", "KRYW", "KEDC", "KGTU",
    "MC2989",
    "KTXAUSTI95"
]


graph_list = {
    'Outside': {
        'sensors':('Toutside', 'Tdoutside'),
        'title':"Outside Temperatures & Dewpoint",

        'dt':1.2,
        'junk':('curr','24','min','max'),
        'legend':False
        },

    'anal': {
        'sensors':('Toutside', 'Tac_dist'),
        'title':"test graph",
        'dt':1.0
        },

    'Humidity': {
        'sensors':('Hthermostat', 'Tdthermostat', 'Hout', 'Tdoutside'),
        'title':'Humidity and Dewpoint',
        'dt':1.0
        },

    'WaterVapor':{
        'sensors':('WVinside','WVoutside'),
        'title':'Inside water vapor partial pressure',
        'dt':1.0
        },

    'Rain24': {
    	'sensors':('RainAcc',) ,
        'title':"Total Rainfall",
        'dt':1,
        'delta':True
        },

    'Rain365': {
    	'sensors':('RainAcc',) ,
        'title':"Yearly Rainfall",
        'dt':365
        },

    'Rain3year': {
    	'sensors':('RainAcc',) ,
        'title':"Three Year Rainfall",
        'dt':1095
        },

    'Wind': {
    	'sensors':('Wspeed', 'Wgust'), 
        'title':"Windspeed",
        'dt':1.0, 'y_lim':(0,30),
   	},

    'Whead': {
    	'sensors':('Whead',),
        'title':"Wind Heading",
        'dt':1.0, 'y_lim':(0,360)
   	},

    'Pressure': {
    	'sensors':('Pambient',),
        'dt':1.0
        },

    'Inside': {
    	'sensors':('Tthermostat', 'Tkitchen', 'Tmaster_br', 'Tw_br', 'Te_br',),
        'title':"Inside Temperatures",
        'dt':1.0
        },

    'Home': {
        'sensors':('Tthermostat', 'Tkitchen', 'Tmaster_br', 
                   'Toutside', 'Hthermostat', 'Tdoutside'),
        'title':"Home Summary",
        'dt':1.0
        },

    'WxSummary': {
        'sensors':('Toutside','Tdoutside',
                   'Wspeed','Wgust',),
        'dt':1.1, 'legend':False,
        'junk':('curr','24','min','max'),
        },

    'Fridge': {
        'sensors':('Tfridge', 'Tfreezer'),
        'dt':1.0, 'y_lim':(-20, 80),
        'junk':('mean','min','max'),
        },
    
    'AC': {
        'sensors':('Toutside', 'Tattic', 'Tac_closet', 'Tac_return', 'Tac_dist'),
        'title':"Air Conditioning Performance",
        'dt':1.0
        },
}


def init_sensor_list(server, all_sensors):
    """Set up the OwConfig sensor list from a list of all sensors on the buss"""
    for n,s in sensor_list.items():
        if s['label'] == 'derived':
            del sensor_list[n]
        else:
            s['value'] = None
            s['time'] = None
            s['tv'] = OwLib.TimeValueHistory(s['depth'])

    missing=[]

    for name,s in sensor_list.items():
        if s['ignore'] or s['label']=='derived':
            continue
        label=s['label']
        if not owaddrs.has_key(label):
            continue
        uid = owaddrs[label]
        if uid in all_sensors:
            s['sensor'] = all_sensors[uid];
            s['server'] = server
            if s['rate'] < 60:
                s['sensor'].useCache(False)
        else:
            missing.append(label)

    if debug>2:
        import pprint
        pp = pprint.PrettyPrinter(indent=3)
        pp.pprint(sensor_list)

    return
