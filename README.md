Convert Sercomm Speedport Plus (VDSL2 modem) status information in a format which can be parsed by the Home assistant `command_line` sensor platform.

## Exported statistics

| vdsl_atnd | Downstream Attenuation (dB) |
| vdsl_atnu | Upstream Attenuation (dB) |
| dsl_crc_errors | CRC errors (total since last DSL sync) |
| dsl_fec_errors | FEC errors (total since last DSL sync) |
| dsl_snrd | Downstream SNR (dB) |
| dsl_snru | Upstream SNR (dB |
| dsl_downstream | Downstream DSL throughput (Kbps) |
| dsl_upstream | Upstream DSL throughput (Kbps) | 
| dsl_max_downstream | Max attainable downstream DSL throughput (Kbps) |
| dsl_max_upstream | Max attainable upstream DSL throughput (Kbps) |
| uptime | Time since the DSL synchronization |
| uptime_online | Time since IP connectivity was established (usually 3-10 seconds after sync)
| dsl_sync_status | "Online" if DSL is synced, "offline" otherwise |
| dsl_online_status | "Online" if IP connectivity has been established, "offline" otherwise |
| dsl_transmission_mode | Transmission mode as reported by the modem (e.g. "VDSL2-17A Annex B") |
| firmware_version | Modem firmware version |



## Usage within Home Assistant

For now the installation is manual but it is quite simple for anyone familiar with Home assistant.


**1. Download the speedport_plus.py script** 

Create a folder named `scripts_cli` under your `/config` Home assistant folder and download there the `speedport_plus.py` script from this repo. 
If you are new to Home assistant, consider the following ways to do that:  

- If you have installed the "Samba share" addon, you may download the script first in your computer and then create the folder and copy-paste the file by accessing the "/config" share.
- If you have installed the "Terminal & SSH addon", you may `mkdir config/scripts_cli && cd config/scripts_cli` and download the script using `wget` and the **raw** github path to the script. You may also use `git` and clone this repo there.
- If you have installed the "File editor" addon, you may manually create the folder from the menu (top left folder icon) and then create a new file, name it `speedport_cli.py` and copy-paste the contents from this repo.

All 3 addons are recommended for productive use and management of Home assistant, so you may try all suggestions above.


**2. Configure the new sensor in configuration.yaml**

After you have successfully added the script under `scripts_cli/speedport_plus.py`, you may edit `configuration.yaml` and create a sensor of platform: [command_line](https://www.home-assistant.io/integrations/sensor.command_line/):

```
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
```


**Configure the router IP**

If the IP of your router is not `192.168.1.1` or if you want to use a hostname, then supply the http base url 
(including `http://` but without a trailing slash `/`) as the first argument (quoted). For instance if the IP of your router is `10.0.50.1` change the configuration above as follows:

```
      command: 'python3 /config/scripts_cli/speedport_plus.py "http://10.0.50.1"'
```


**Polling interval**

The configuration suggested above will use a default `scan_interval: 60` which means that you will get statistics from
your modem every 60 seconds. You can lower it below 60 seconds but the amount of storage
required to store the statistics will increase accordingly. If you only care about long term statistics
and don't care to catch short term spikes, you may want to increase it to 300 seconds (5 minutes).

**DSL status Vs Internet status**

The configuration suggested above will use the DSL synchronization status as the "online/offline" status of the sensor. You may 
want to change it to indicate full IP connectivity instead (i.e. you have an active PPPoE session). You
can do this by changing the `value_template` field as:

```
      value_template: '{{ value_json.dsl_online_status }}'
```

(we changed `dsl_link_status` to `dsl_online_status`)



**3. Restart Home assistant and then create widgets or automations**

Restart Home assistant and the new sensor will be available as the entity "speedport_plus_status". You may add the new sensor to your dashboards or create automations.

The new sensor entity `speedport_plus_status` will have the values "online" or "offline". The DSL line metrics (attenuation, snr, sync speed etc.) will be available as attributes of this entity. 

You may use the sensor status (online/offline) in automations (for instance restart your router with a smart plug when disconnected) as well as the numberic attributes (using trigger `numeric_state` and selecting an attribute).

Monitoring your Internet connection long term may be more practical with a tool such as Grafana. Read the related section below.


## InfluxDB / Grafana usage
    
If you have integrated Home assistant with [InfluxDB](https://www.home-assistant.io/integrations/influxdb/), the
attributes (DSL speed, snr, attenuation etc.) will be also available as seperate "fields" in the default "state" measurement.

InfluxDB and Grafana are available as Home assistant (community) addons. Check the Add-on Store under the Supervisor section.

As an example, in Grafana if you want to plot the downstream SNR, you have to choose in the Visual editor:

```
FROM default state WHERE entity_id = speedport_plus_status
SELECT field(dsl_snrd) last()
GROUP BY time($__interval) tag(entity_id) fill(none)
```

In text query mode, this is:

```
SELECT last("dsl_snrd") FROM "state" WHERE ("entity_id" = 'speedport_plus_status') AND $timeFilter GROUP BY time($__interval) fill(none)
```

(`AND $timeFilter` is added by Grafana to allow filtering by time using the top right dropdown menu)

This assumes that you use `state` as the [default measurement](https://www.home-assistant.io/integrations/influxdb/#configuration-variables) name when a metric is "unitless". i.e. in `configuration.yaml` you have:

```
influxdb:
    ...
    default_measurement: state
    ...
```

If it's not the case, then you should adjust the queries above accordingly.



**Rate instead of total stats**

You may compute rates (e.g. errors per minute) instead of totals using InfluxDB transformation functions such as: `non_negative_difference()` and `non_negative_derivative()` 


## Related helpful integrations


**[UPnP/Internet Gateway Device (IGD)](https://www.home-assistant.io/integrations/upnp/)**

If you have UPnP enabled on your router, Home assistant will detect it and offer to add the integration (or you may check manually from the integrations page).
This will output traffic statistics from your home network. It's not very consistent with this modem but when it works it may provide an indication of (some of) your traffic.


**[Ping (ICMP) Binary sensor](https://www.home-assistant.io/integrations/ping/)**

The ping integration is usually used for presence detection. But you may also use it to check your Internet latency.

```
binary_sensor:
  - platform: ping
    host: hostname-or-ip-address-to-ping
    name: "ISP Ping"
    count: 3
    scan_interval: 3600
```

The above example will ping "hostname-or-ip-address-to-ping" 3 times every 1 hour (3600 seconds).

The sensor exposes the different round trip times values measured by ping as attributes: round trip time mdev, round trip time avg, round trip time min, round trip time max.


**[Speedtest.net](https://www.home-assistant.io/integrations/speedtestdotnet/) Integration**

You may measure your true download and upload speeds and your ping (latency) with the Speedtest.net integration. 
This way you can compare your DSL sync speed with your actual speed.

Configure the integration from the UI per the instructions in the linked page above. 

- It is advised to not run the test very frequently because it will clog your connection on unpredictable times. I have changed the default to 360 minutes (6 hours).
- It is suggested to set a specific server close to you (see the dropdown in the "Options" menu) so you have consistent results to compare long term.

Note that a Raspberry PI (other than 4B or newer) may limit the reported maximum speed to 100Mbps or 300Mbps (Raspberry PI 3+) due to the slower LAN adapter. 
Also note that this integration uses [speedtest-cli](https://github.com/sivel/speedtest-cli) which may be a little slower than the results you get on Speedtest.net. 
Your true latency may be 7-10ms lower than what is reported from this tool. Read more [here](https://github.com/sivel/speedtest-cli#inconsistency). 
The ping integration mentioned previously is more accurate for measuring latency.

Alternatively you may use the [Iperf3](https://www.home-assistant.io/integrations/iperf3/) or the [Fast.com](https://www.home-assistant.io/integrations/fastdotcom/) integrations.




## Test from the command-line

You may test the script from your PC (if you have python3 installed) or from the Home assistant command line.

Run without arguments to retrieve data from the default url <http://192.168.1.1/data/Status.json>:

```
python3 speedport_plus.py
```  

If the IP of your router is not `192.168.1.1` or if you want to use a hostname, then supply the http base url 
(including "http://" but without a trailing slash) as the first argument (quoted). For example:

```
python3 speedport_plus.py "http://10.0.50.1"
```



