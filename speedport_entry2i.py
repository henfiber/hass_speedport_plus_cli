#!/usr/bin/python3

"""
  Helper script to convert Speedport Entry 2i (modem) status information
  in a format to be parsed by the Home assistant command_line sensor 
  platform.

  Usage from the command-line:
    Run without arguments to retrieve data 
    from the default url "http://192.168.1.1/common_page/status_info_lua.lua"
    i.e. run as:
  
    python3 speedport_entry2i.py
  
    If the IP of your router is not 192.168.1.1 or if you want 
    to use a hostname, then supply the http base url 
    (including "http://" but without a trailing slash) as the 
    first argument (quoted). For example:
  
    python3 speedport_entry2i.py "http://10.0.50.1"
  
  Usage within Home Assistant:
    Add a sensor of platform: command_line
    e.g.
    
    sensor:
        - platform: command_line
          name: Speedport Entry2i status
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
          command: 'python3 /config/scripts_cli/speedport_entry2i.py "http://192.168.1.1"'
          value_template: '{{ value_json.dsl_link_status }}'
    
    The new sensor entity "speedport_entry2i_status" will have 
    the values "online" or "offline"
    
    The DSL line metrics (attenuation, snr, sync speed etc.) will
    be available as attributes of this entity. 
"""

import json
from datetime import datetime
import urllib.request
from urllib.error import HTTPError, URLError
import sys

# Required for Speedport Entry 2i (XML output)
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

# Default base url and Argument handling
speedport_base_url = "http://192.168.1.1"

if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
    speedport_base_url = sys.argv[1]

speedport_full_url = speedport_base_url \
                   + "/common_page/status_info_lua.lua" \
                   + "?_=" \
                   + str(int(datetime.now().timestamp() * 1000))


# using urllib to avoid dependency on requests module
req = urllib.request.Request(speedport_full_url)
req.add_header('Accept-Language', 'en')

try:
    f = urllib.request.urlopen(req)
    xml_data = f.read().decode('utf-8')
except URLError as e:
    print(e, file=sys.stderr)
    print('{"dsl_link_status": "offline"}')
    exit(3)
finally:
    f.close()


# the dictionary which will store the final results (will output as json)
js = {}

# Mapping from original field names to Speedport Plus names for consistency
# We verified that LEDStatus is the "Internet status" looking at the jquery code
# "Atuc_fec_errors" were verified as Downstream FEC errors by matching the number with 
# what was printed in the UI.
# "Module_type" is printed as "transmission mode" in the UI
vars_map = dict(
    Downstream_attenuation = "vdsl_atnd",
    Upstream_attenuation = "vdsl_atnu",
    DownCrc_errors = "dsl_crc_errors_down",
    UpCrc_errors = "dsl_crc_errors_up",
    Atuc_fec_errors = "dsl_fec_errors_down",
    Fec_errors = "dsl_fec_errors_up",
    Downstream_noise_margin = "dsl_snrd",
    Upstream_noise_margin = "dsl_snru",
    Downstream_current_rate = "dsl_downstream",
    Upstream_current_rate = "dsl_upstream",
    SoftwareVer = "firmware_version",
    Module_type = "dsl_transmission_mode",
    Status = "dsl_link_status",
    LEDStatus = "dsl_online_status"
)

# Parse the XML response
try:
    root = ET.fromstring(xml_data)
except ParseError as e:
    print(e, file=sys.stderr)
    exit(4) 

# Check if the XML root element is what we expect
if root.tag != "ajax_response_xml_root":
    print("Unexpeced XML format", file=sys.stderr)
    exit(5)


# Find the ParaName,ParaValue elements with XPath and iterate
# The keys and values are written in series. 
# Therefore when we find a "ParaName" we store the inner text as the "current" key
# when we find a "ParaValue" we store the inner text as the value of the "current" key
# If a key is not found in the vars_map dictionary we ignore it.
for el in root.findall(".//Instance/*"):
    if el.tag == "ParaName":
        xml_key = el.text
    elif el.tag == "ParaValue":
        if xml_key in vars_map:
            js[vars_map.get(xml_key)] = el.text




# sum FEC and CRC errors and remove the original variables
if "dsl_fec_errors_down" in js and "dsl_fec_errors_up" in js:
    js['dsl_fec_errors'] = int(js.get('dsl_fec_errors_down')) + int(js.get('dsl_fec_errors_up'))
    del js['dsl_fec_errors_down']
    del js['dsl_fec_errors_up']
if "dsl_crc_errors_down" in js and "dsl_crc_errors_up" in js:
    js['dsl_crc_errors'] = int(js.get('dsl_crc_errors_down')) + int(js.get('dsl_crc_errors_up'))
    del js['dsl_crc_errors_down']
    del js['dsl_crc_errors_up']


# Change DSL/Internet status Up/Down to Online/Offline
js['dsl_link_status'] = "online" if js.get('dsl_link_status') in ("Up", "online") else "offline"
js['dsl_online_status'] = "online" if js.get('dsl_online_status') in ("Up", "online") else "offline"


# Divide SNR and Attenuation values by 10 and round in 1 decimal
js["dsl_snrd"] = round(int(js.get("dsl_snrd")) / 10, 1)
js["dsl_snru"] = round(int(js.get("dsl_snru")) / 10, 1)
js["vdsl_atnd"] = round(int(js.get("vdsl_atnd")) / 10, 1)
js["vdsl_atnu"] = round(int(js.get("vdsl_atnu")) / 10, 1)



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


