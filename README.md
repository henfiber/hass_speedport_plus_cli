Integrate Sercomm Speedport Plus (VDSL2 modem) with Home assistant using the `command_line` sensor platform.

![HASS Speedport plus dashboard - Screenshot](screenshots/hass_speedport-plus_dashboard.png)


**Exported statistics**

| Attribute | Description |
| ----------| ----------- |
| vdsl_atnd | Downstream Attenuation (dB) |
| vdsl_atnu | Upstream Attenuation (dB) |
| dsl_crc_errors | CRC errors (total since last DSL sync) |
| dsl_fec_errors | FEC errors (total since last DSL sync) |
| dsl_snrd | Downstream SNR (dB) |
| dsl_snru | Upstream SNR (dB) |
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


**1. Download the speedport_plus.py script** 

Create a folder named `scripts_cli` under your `/config` Home assistant folder and download there the `speedport_plus.py` script from this repo. 
If you are new to Home assistant, consider the following ways to do that:  

- If you have installed the "Samba share" addon, you may download the script first in your computer and then create the folder and copy-paste the file by accessing the "/config" share.
- If you have installed the "Terminal & SSH addon", you may `mkdir config/scripts_cli && cd config/scripts_cli` and download the script using `wget` and the **raw** github path to the script. You may also use `git` and clone this repo there.
- If you have installed the "File editor" addon, you may manually create the folder from the menu (top left folder icon) and then create a new file, name it `speedport_plus.py` and copy-paste the contents from this repo.

All 3 addons are recommended for productive use and management of Home assistant, so you may try any of the suggestions above.


**2. Configure the new sensor in configuration.yaml**

After you have successfully added the script under `scripts_cli/speedport_plus.py`, you may edit `configuration.yaml` and create a sensor of platform: [command_line](https://www.home-assistant.io/integrations/sensor.command_line/):

```yaml
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

If the IP of your router is not `192.168.1.1` or if you want to use a hostname, then change `command:` above with the correct http base url 
(including `http://` but without a trailing slash `/`) as the first argument (quoted). For instance if the IP of your router is `10.0.50.1` change the configuration above as follows:

```yaml
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

```yaml
      value_template: '{{ value_json.dsl_online_status }}'
```

(`dsl_link_status` was changed to `dsl_online_status`)



**3. Restart Home assistant and then create widgets or automations**

Restart Home assistant and the new sensor will be available as the entity "speedport_plus_status". You may add the new sensor to your dashboards or create automations.

The new sensor entity `speedport_plus_status` will have the values "online" or "offline". The DSL line metrics (attenuation, snr, sync speed etc.) will be available as attributes of this entity. 

![HASS Speedport plus status - Screenshot](screenshots/hass_speedport_plus_status-and-attributes.png)

You may use the sensor status (online/offline) in automations (for instance, restart your router with a smart plug when disconnected). You may also use the numeric attributes using trigger `numeric_state` and selecting an attribute from the list.

Monitoring your Internet connection long term may be more practical with a tool such as Grafana. A sample dashboard is included in this repo. Read the following section for more.


## Attributes as individual sensors

If you want to make some of the DSL attributes available as individual sensors (useful for UI widgets), you may accomplish this with template sensors:

```yaml
sensor:
    - platform: template
      sensors:
          dsl_sync_downstream:
              friendly_name: DSL Sync downstream
              value_template: >-
                  {{state_attr("sensor.speedport_plus_status", "dsl_downstream") | float | multiply(0.001) | round(2) }}
              unit_of_measurement: "Mbit/s"
          dsl_sync_upstream:
              friendly_name: DSL Sync upstream
              value_template: >-
                  {{state_attr("sensor.speedport_plus_status", "dsl_upstream") | float | multiply(0.001) | round(2) }}
              unit_of_measurement: "Mbit/s"
          dsl_errors_crc:
              friendly_name: DSL CRC Errors
              value_template: >-
                  {{state_attr("sensor.speedport_plus_status", "dsl_crc_errors") }}
          dsl_errors_fec:
              friendly_name: DSL FEC Errors
              value_template: >-
                  {{state_attr("sensor.speedport_plus_status", "dsl_fec_errors") }}
```

You may also want to compute error rates which are more useful than totals for detecting spikes during the day. We can use the 
Home assistant [derivative](https://www.home-assistant.io/integrations/derivative/) platform to accomplish that. 

(Make sure you have added the invidual sensors as suggested above first)

```
sensor:
    - platform: derivative
      source: sensor.dsl_errors_crc
      name: DSL Error rate (CRC)
      round: 0
      unit_time: h
      unit: "Err/h"
      time_window: "00:05:00"  # we look at the change over the last 5 minutes
    - platform: derivative
      source: sensor.dsl_errors_fec
      name: DSL Error rate (FEC)
      round: 0
      unit_time: h
      unit: "Err/h"      
      time_window: "00:05:00"  # we look at the change over the last 5 minutes
```



## InfluxDB / Grafana usage

![Speedport plus Grafana Dashboard - Screenshot](screenshots/hass_grafana_speedport-plus_dashboard.png)

If you have integrated Home assistant with [InfluxDB](https://www.home-assistant.io/integrations/influxdb/), the
attributes (DSL speed, snr, attenuation etc.) will be also available as seperate "fields" in the default "state" measurement.

InfluxDB and Grafana are available as Home assistant (community) addons. Check the Add-on Store under the Supervisor section.

The dashboard displayed here is available in this repo under the `Grafana` folder. You may import it into your Grafana instance choosing your InfluxDB data source.


**Sample queries**

In Grafana, if you want to plot the downstream SNR, then you have to choose in the **Visual editor**:

```SQL
FROM default state WHERE entity_id = speedport_plus_status
SELECT field(dsl_snrd) last()
GROUP BY time($__interval) tag(entity_id) fill(none)
```

(this is not an actual InfluxDB query, just the way Grafana UI editor displays the query parts)


In text query mode, this is:

```SQL
SELECT last("dsl_snrd") FROM "state" WHERE ("entity_id" = 'speedport_plus_status') AND $timeFilter GROUP BY time($__interval) fill(none)
```

(`AND $timeFilter` is added by Grafana to allow filtering by time using the top right dropdown menu)

This assumes that you use `state` as the [default measurement](https://www.home-assistant.io/integrations/influxdb/#configuration-variables) name when a metric is "unitless". i.e. in `configuration.yaml` you have:

```yaml
influxdb:
    ...
    default_measurement: state
    ...
```

If it's not the case, then you should adjust the queries above accordingly.



**Rates instead of total stats**

You may compute rates (e.g. errors per minute) instead of totals using InfluxDB transformation functions such as: `non_negative_difference()` and `non_negative_derivative()`.  
Or just use the Home assistant [derivative](https://www.home-assistant.io/integrations/derivative/) platform as described in the previous section.



## Related helpful integrations


**[UPnP/Internet Gateway Device (IGD)](https://www.home-assistant.io/integrations/upnp/)**

If you have UPnP enabled on your router, Home assistant will detect it and offer to add the integration (or you may check manually from the integrations page).
This will output traffic statistics from your home network. It's not very consistent with this modem but when it works it may provide an indication of (some of) your traffic.


**[Ping (ICMP) Binary sensor](https://www.home-assistant.io/integrations/ping/)**

The ping integration is usually used for presence detection. But you may also use it to check your Internet latency.

```yaml
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

You may test the script from your PC (if you have python3 installed).

Run without arguments to retrieve data from the default url <http://192.168.1.1/data/Status.json>:

```sh
python3 speedport_plus.py
```  

If the IP of your router is not `192.168.1.1` or if you want to use a hostname, then supply the http base url 
(including "http://" but without a trailing slash) as the first argument (quoted). For example:

```sh
python3 speedport_plus.py "http://10.0.50.1"
```



