#!/usr/bin/python3

"""
  Helper script to convert Speedport Plus (Sercomm) status information
  in a format to be parsed by the Home assistant command_line sensor 
  platform.

  Usage from the command-line:
    Run without arguments to retrieve data 
    from the default url "http://192.168.1.1/data/Status.json"
    i.e. run as:
  
    python3 speedport_plus.py
  
    If the IP of your router is not 192.168.1.1 or if you want 
    to use a hostname, then supply the http base url 
    (including "http://" but without a trailing slash) as the 
    first argument (quoted). For example:
  
    python3 speedport_plus.py "http://10.0.50.1"
  
  Usage within Home Assistant:
    Add a sensor of platform: command_line
    e.g.
    
    sensor:
        - platform: command_line
          name: Speedport Plus status
          scan_interval: 60
          json_attributes:
            - vdsl_atnu
            - vdsl_atnd
            - dsl_crc_errors
            - dsl_fec_errors
            - dsl_snrd
            - dsl_snru
            - dsl_downstream
            - dsl_upstream
            - dsl_max_downstream
            - dsl_max_upstream
            - uptime
            - uptime_online
            - dsl_online_status
            - dsl_transmission_mode
            - firmware_version
          command: 'python3 /config/scripts_cli/speedport_plus.py "http://192.168.1.1"'
          value_template: '{{ value_json.dsl_link_status }}'
    
    The new sensor entity "speedport_plus_status" will have 
    the values "online" or "offline"
    
    The DSL line metrics (attenuation, snr, sync speed etc.) will
    be available as attributes of this entity. 
"""

import json
from datetime import datetime
import urllib.request
import sys

# Default base url
speedport_plus_base_url = "http://192.168.1.1"

# Argument handling
if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
    speedport_plus_base_url = sys.argv[1]

speedport_status_json_full_url = speedport_plus_base_url + "/data/Status.json"


# Retrieve the status json data from the router url
req = urllib.request.Request(speedport_status_json_full_url)
req.add_header('Accept-Language', 'en')

try:
    f = urllib.request.urlopen(req)
    try:
        data = json.loads(f.read().decode('utf-8'))
    except ValueError as e2:
        print(e2, file=sys.stderr)
        print('{"dsl_link_status": "offline"}')        
        exit(2)
except URLError as e:
    print(e, file=sys.stderr)
    print('{"dsl_link_status": "offline"}')
    exit(3)
finally:
    f.close()



# keep these variables
vars_keep = ["vdsl_atnu", "vdsl_atnd", 
             "dsl_crc_errors", "dsl_fec_errors",
             "dsl_snr",
             "dsl_downstream", "dsl_upstream", 
             "dsl_max_downstream", "dsl_max_upstream", 
             "dsl_link_status", 
             "dsl_online_time", 
             "dsl_sync_time", 
             "datetime",
             "dsl_transmission_mode",
             "firmware_version"]

# convert the json to HA parseable format
js = {doc['varid']:doc['varvalue'] for doc in data if doc['varid'] in vars_keep}


# split SNR string to downstream and upstream values
if js.get('dsl_snr'):
    js['dsl_snrd'] = js['dsl_snr'].split(" / ")[0]
    js['dsl_snru'] = js['dsl_snr'].split(" / ")[1]
    del js['dsl_snr']


# compute new attributes "uptime" and "uptime_online" for DSL uptime 
# and IP-connectivity uptime respectively (in seconds)
# Also add a new attribute: "dsl_online_status" to signify confirmed IP connectivity
# (the reported attribute "dsl_link_status" is for DSL link only)
if js.get('datetime'):
    now = datetime.strptime(js['datetime'], '%Y-%m-%d %H:%M:%S')
    # IP connectivity uptime
    if js.get('dsl_online_time'):
        online_time = datetime.strptime(js['dsl_online_time'], '%Y-%m-%d %H:%M:%S')
        js['uptime_online'] = int((now - online_time).total_seconds())
        js['dsl_online_status'] = "online"
    else:
        js['uptime_online'] = 0
        js['dsl_online_status'] = "offline"
    # DSL uptime
    if js.get('dsl_sync_time'):
        sync_time = datetime.strptime(js['dsl_sync_time'], '%Y-%m-%d %H:%M:%S')
        js['uptime'] = int((now - sync_time).total_seconds())    
    else:
        js['uptime'] = 0
        
    # discard datetime strings - we'll keep only uptime (how much time it is up)
    del js['datetime']
    del js['dsl_online_time']
    del js['dsl_sync_time']


# Parse strings to numbers
def try_num(s):
    if isinstance(s, (int, float)):
        return s    
    try:
        s = int(s)
    except ValueError:
        try:
            s = float(s)
        except ValueError:
            return s
        return s
    return s

js = {varid:try_num(varvalue) for (varid, varvalue) in js.items()}


# Output the final json
print(json.dumps(js))
