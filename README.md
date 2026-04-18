<b>
In this repository, I'll demonstrate how to monitor the parameters of a Tuya smart device using a Python script.

To retrieve data from the device via the API, you need to create an account with the Tuya Developer Link: https://developer.tuya.com/en/
and create a free Tuya cloud project.

Once we have the project created, we can go to device debugging and search for the data we want to monitor – in my case, I want to monitor the real-time data of the smart socket, including energy consumption readings.


</b>




<img width="1918" height="719" alt="image" src="https://github.com/user-attachments/assets/2823b6e9-9512-4461-97aa-dd79ae564cb4" />

<img width="1918" height="736" alt="image" src="https://github.com/user-attachments/assets/fc0da116-cdb0-4d08-bc2f-032f33cf515c" />


<img width="1916" height="915" alt="image" src="https://github.com/user-attachments/assets/774cfe2a-752c-43c9-9ae5-26f5960cd7ec" />


Simple data, such as current power consumption and voltage, are visible in a standard query, while data such as the accumulated daily consumption must be retrieved using a query that displays kWh consumed approximately every half hour.

<img width="1917" height="920" alt="image" src="https://github.com/user-attachments/assets/6cfc1022-60fb-497a-ac19-8966296408fd" />

sum “value” = 359 ~ 0.36KWh 

<img width="738" height="1600" alt="image" src="https://github.com/user-attachments/assets/f98293b7-8860-4772-b3d2-f1803405f714" />

The summed values ​​from the query match the readings from the application. As you can see, the value is rounded to two decimal places.


Install the phyton package on the Zabbix server:
apt install -y python3-venv
//Installs a module that allows you to create isolated Python environments
python3 -m venv /opt/zabbix/tuya/venv
//Creates a separate Python environment in: /opt/zabbix/tuya/venv
source /opt/zabbix/tuya/venv/bin/activate
//Activates venv
pip install tuya-iot-py-sdk
//Installs the Tuya SDK

Zabbix server user-related commands for the script:

useradd -r -s /bin/false tuya
//useradd – creates a user on Linux
//-r – system user (no home directory, no login)
//-s /bin/false – cannot log in as this user

mkdir -p /opt/zabbix/tuya
chown -R tuya:tuya /opt/zabbix/tuya
//chown -R tuya:tuya – sets the owner



Command to create the script:
nano /opt/zabbix/tuya/tuya_device.py

<pre> ```python # 
#!/opt/zabbix/tuya/venv/bin/python
import json
import datetime
import time

from tuya_iot import TuyaOpenAPI, TUYA_LOGGER


# ================= KONFIGURACJA =================
ACCESS_ID = "TUYA_ACCESS_ID"
ACCESS_KEY = "TUYA_ACCESS_KEY"
USERNAME = "EMAIL_DO_TUYA"
PASSWORD = "HASLO_DO_TUYA"
DEVICE_ID = "ID_URZADZENIA"

ENDPOINT = "https://openapi.tuyaeu.com"
COUNTRY_CODE = "48"
APP_SCHEMA = "smartlife"

# Opcjonalnie debug
# TUYA_LOGGER.setLevel("DEBUG")


# ================= TUYA =================
openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
openapi.connect(USERNAME, PASSWORD, COUNTRY_CODE, APP_SCHEMA)



# ================= STATUS (MOC, NAPIĘCIE ITD.) =================
resp = openapi.get(f"/v1.0/iot-03/devices/{DEVICE_ID}/status")

dp = {i["code"]: i["value"] for i in resp.get("result", [])}

cur_power_w = dp.get("cur_power", 0) / 10      # 185 → 18.5 W
cur_voltage_v = dp.get("cur_voltage", 0) / 10
cur_current_a = dp.get("cur_current", 0) / 1000
switch_1 = int(dp.get("switch_1", 0))

# ================= OKRES DZISIEJSZY (CAŁY DZIEŃ) =================
now = datetime.datetime.now()

start_day = datetime.datetime.combine(
    now.date(),
    datetime.time(0, 0, 0)
)

end_day = datetime.datetime.combine(
    now.date(),
    datetime.time(23, 59, 59)
)

start_ts = int(start_day.timestamp() * 1000)
end_ts = int(end_day.timestamp() * 1000)


# ================= REPORT-LOGS (ENERGIA DZIENNA) =================
logs_resp = openapi.get(
    f"/v2.0/cloud/thing/{DEVICE_ID}/report-logs",
    {
        "codes": "add_ele",
        "start_time": start_ts,
        "end_time": end_ts,
        "size": 100
    }
)

energy_wh = 0

# KLUCZOWA POPRAWKA – logs może NIE ISTNIEĆ
if logs_resp.get("success"):
    result = logs_resp.get("result", {})
    logs = result.get("logs", [])  # <-- jeśli brak, dostaniemy []

    for log in logs:
        try:
            energy_wh += int(log.get("value", 0))  # add_ele = Wh
        except ValueError:
            pass
else:
    energy_wh = 0

energy_delta_kwh = round(energy_wh / 1000, 6)

# ================= OUTPUT DO ZABBIX =================
output = {
    "switch_1": switch_1,
    "power_w": round(cur_power_w, 3),
    "voltage_v": cur_voltage_v,
    "current_a": round(cur_current_a, 3),
    "energy_delta_kwh": energy_delta_kwh
}

print(json.dumps(output))

</pre>



The command to change the script permissions to block access for the rest of the system:
chown tuya:tuya /opt/zabbix/tuya/tuya_device.py
chmod 750 /opt/zabbix/tuya/tuya_device.py




ln -s /opt/zabbix/tuya/tuya_device.py /usr/lib/zabbix/externalscripts/tuya_device.py
chown -h zabbix:zabbix /usr/lib/zabbix/externalscripts/tuya_device.py

Create a script link in the Zabbix directory and set the link owner to the zabbix user so that Zabbix can see and run the script from the correct location:
ln -s /opt/zabbix/tuya/tuya_device.py /usr/lib/zabbix/externalscripts/tuya_device.py
chown -h zabbix:zabbix /usr/lib/zabbix/externalscripts/tuya_device.py

Test what the script returns:

<pre>
(venv) root@zabbix:~# python3 ./tuya_device.py
[2025-12-20 23:50:35,129] [tuya-openapi] Request: method = POST,                 url = https://openapi.tuyaeu.com/v1.0/iot-01/associated-users/actions/authorized-login,                params = None,                body = {'username': 'xxx@gmail.com', 'password': '***', 'country_code': '44', 'schema': 'tuyaSmart'},                t = 1766271035129
[2025-12-20 23:50:35,377] [tuya-openapi] Response: {
  "result": {
    "access_token": "***",
    "expire_time": 7200,
    "platform_url": "https://openapi.tuyaeu.com",
    "refresh_token": "***",
    "uid": "***"
  },
  "success": true,
  "t": 1766271035362,
  "tid": "xxx"
}
[2025-12-20 23:50:35,377] [tuya-openapi] Request: method = GET,                 url = https://openapi.tuyaeu.com/v1.0/iot-03/devices/bf184xxx/status,                params = None,                body = None,                t = 1766271035377
[2025-12-20 23:50:35,463] [tuya-openapi] Response: {
  "result": [
    {
      "code": "switch_1",
      "value": true
    },
    {
      "code": "countdown_1",
      "value": 0
    },
    {
      "code": "add_ele",
      "value": 8
    },
    {
      "code": "cur_current",
      "value": 198
    },
    {
      "code": "cur_power",
      "value": 172
    },
    {
      "code": "cur_voltage",
      "value": 2342
    },
    {
      "code": "relay_status",
      "value": "power_on"
    },
    {
      "code": "light_mode",
      "value": "none"
    },
    {
      "code": "child_lock",
      "value": false
    },
    {
      "code": "cycle_time",
      "value": ""
    },
    {
      "code": "random_time",
      "value": ""
    },
    {
      "code": "switch_inching",
      "value": ""
    },
    {
      "code": "overcharge_switch",
      "value": false
    }
  ],
  "success": true,
  "t": 1766271035447,
  "tid": "xxx"
}
[2025-12-20 23:50:35,463] [tuya-openapi] Request: method = GET,                 url = https://openapi.tuyaeu.com/v2.0/cloud/thing/bf184xxx/report-logs,                params = {'codes': 'add_ele', 'start_time': 1766185200000, 'end_time': 1766271035463, 'size': 100},                body = None,                t = 1766271035463
[2025-12-20 23:50:35,814] [tuya-openapi] Response: {
  "result": {
    "device_id": "bf184xxx",
    "has_more": false,
    "logs": [
      {
        "code": "add_ele",
        "event_time": 1766269680000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766267881000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766266083000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766264285000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766262487000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766260688000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766258890000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766257092000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766255294000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766253495000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766251697000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766249899000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766248101000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766246303000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766244504000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766242706000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766240908000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766239110000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766237311000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766235513000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766233721000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766231923000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766230125000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766228327000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766226528000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766224730000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766222932000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766221134000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766219335000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766217537000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766215739000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766213941000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766212142000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766210344000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766208546000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766206748000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766204950000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766203151000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766201353000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766199555000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766197757000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766195958000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766194160000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766192362000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766190564000,
        "value": "8"
      },
      {
        "code": "add_ele",
        "event_time": 1766188766000,
        "value": "7"
      },
      {
        "code": "add_ele",
        "event_time": 1766186967000,
        "value": "7"
      }
    ],
    "total": 1000
  },
  "success": true,
  "t": 1766271035799,
  "tid": "xxx"
}
{"switch_1": 1, "power_w": 17.2, "voltage_v": 234.2, "current_a": 0.198, "energy_delta_kwh": 0.361}
    
</pre>


Adding a Host - without an interface. Data will be collected from the "Master Item" value added
<img width="1047" height="558" alt="image" src="https://github.com/user-attachments/assets/1bb8bc73-f43e-403f-a40e-2e505d47cbc2" />

Master Item, which runs through the entire script and will be used to display other data of interest to us.
<img width="1045" height="727" alt="image" src="https://github.com/user-attachments/assets/43137332-d49d-44af-84ee-450070ece8a1" />


Adding Item for current power consumption:

<img width="1042" height="677" alt="image" src="https://github.com/user-attachments/assets/2ef4938e-ea5f-401c-aa92-f055707a52da" />

Preprocessing tab, to specify what should be read from the script.
<img width="1048" height="276" alt="image" src="https://github.com/user-attachments/assets/9e21e77e-694c-4a12-9e30-5778047e5074" />

