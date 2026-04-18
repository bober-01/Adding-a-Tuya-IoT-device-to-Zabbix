# 🔌 Tuya Smart Device Monitoring with Python + Zabbix

This repository demonstrates how to monitor parameters of a **Tuya smart device** using a **Python script** and integrate the data into **Zabbix**.

The goal is to achieve both:
- real-time values (power, voltage, current)
- aggregated daily energy consumption (kWh)

<img width="1152" height="214" alt="image" src="https://github.com/user-attachments/assets/161a54d3-66ad-42a0-825a-f1f4cde96e0c" />

<img width="1918" height="693" alt="image" src="https://github.com/user-attachments/assets/e24581e9-b603-47c4-9652-cdb415f6d887" />


---

## 📌 How it works

Tuya API exposes two types of data:

1. **Real-time device status**
   - Available directly via `/status` endpoint
   - Includes values like power, voltage, current

2. **Energy consumption (kWh)**
   - NOT directly available as a single value
   - Must be calculated from logs (`add_ele`)
   - Logs appear approximately every 30 minutes

---

## 🔐 Step 1: Tuya Developer Setup

Create an account:
👉 https://developer.tuya.com/en/

Then:

1. Create a **Cloud Project (free)**
2. Go to:
   ```
   Cloud → API Explorer → Device Debugging
   ```
3. Search for your device
4. Identify datapoints you want to monitor

<img src="https://github.com/user-attachments/assets/2823b6e9-9512-4461-97aa-dd79ae564cb4" />
---

## 📊 Example API Data

### Overview of selected data from DP id

<img src="https://github.com/user-attachments/assets/fc0da116-cdb0-4d08-bc2f-032f33cf515c" />

---

### Energy logs

<img width="1916" height="915" alt="image" src="https://github.com/user-attachments/assets/774cfe2a-752c-43c9-9ae5-26f5960cd7ec" />
<img src="https://github.com/user-attachments/assets/6cfc1022-60fb-497a-ac19-8966296408fd" />

Each entry:
- represents energy usage in **Wh**
- appears roughly every 30 minutes

👉 Example:
```
sum(value) = 359 → 0.36 kWh
```


<img width="738" height="1600" alt="image" src="https://github.com/user-attachments/assets/f98293b7-8860-4772-b3d2-f1803405f714" />

✔️ Summed values match the Tuya mobile app (rounded to 2 decimal places)

---

## 🐍 Step 2: Install Python Environment

```bash
apt install -y python3-venv
```
- Installs module for creating isolated Python environments

```bash
python3 -m venv /opt/zabbix/tuya/venv
```
- Creates a dedicated Python environment for this integration

```bash
source /opt/zabbix/tuya/venv/bin/activate
```
- Activates the virtual environment

```bash
pip install tuya-iot-py-sdk
```
- Installs official Tuya Python SDK

---

## 👤 Step 3: Create Dedicated System User

```bash
useradd -r -s /bin/false tuya
```
- `useradd` → creates a new Linux user  
- `-r` → system user (no home directory)  
- `-s /bin/false` → disables login for security  

```bash
mkdir -p /opt/zabbix/tuya
```
- Creates directory for scripts

```bash
chown -R tuya:tuya /opt/zabbix/tuya
```
- Assigns ownership to the `tuya` user

---

## 🧠 Step 4: Create Python Script

```bash
nano /opt/zabbix/tuya/tuya_device.py
```

### 📜 Script

```python
#!/opt/zabbix/tuya/venv/bin/python
import json
import datetime

from tuya_iot import TuyaOpenAPI

#CONFIG Tuya Connection
ACCESS_ID = "TUYA_ACCESS_ID"
ACCESS_KEY = "TUYA_ACCESS_KEY"
USERNAME = "EMAIL_DO_TUYA"
PASSWORD = "HASLO_DO_TUYA"
DEVICE_ID = "ID_URZADZENIA"

ENDPOINT = "https://openapi.tuyaeu.com"
COUNTRY_CODE = "48"
APP_SCHEMA = "smartlife"

# Optional debug
# TUYA_LOGGER.setLevel("DEBUG")

#CONNECT
openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
openapi.connect(USERNAME, PASSWORD, COUNTRY_CODE, APP_SCHEMA)

#DEVICE STATUS
resp = openapi.get(f"/v1.0/iot-03/devices/{DEVICE_ID}/status")

# Convert list to dictionary
dp = {i["code"]: i["value"] for i in resp.get("result", [])}

# Normalize values (Tuya uses scaled integers)
cur_power_w = dp.get("cur_power", 0) / 10      # e.g. 185 → 18.5 W
cur_voltage_v = dp.get("cur_voltage", 0) / 10
cur_current_a = dp.get("cur_current", 0) / 1000
switch_1 = int(dp.get("switch_1", 0))

#TIME RANGE (TODAY)
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

#ENERGY LOGS
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

# IMPORTANT: logs may not exist
if logs_resp.get("success"):
    result = logs_resp.get("result", {})
    logs = result.get("logs", [])

    for log in logs:
        try:
            energy_wh += int(log.get("value", 0))
        except ValueError:
            pass
else:
    energy_wh = 0

# Convert Wh → kWh
energy_delta_kwh = round(energy_wh / 1000, 6)

#OUTPUT
output = {
    "switch_1": switch_1,
    "power_w": round(cur_power_w, 3),
    "voltage_v": cur_voltage_v,
    "current_a": round(cur_current_a, 3),
    "energy_delta_kwh": energy_delta_kwh
}

print(json.dumps(output))
```

---

## 🔐 Step 5: Secure Script

```bash
chown tuya:tuya /opt/zabbix/tuya/tuya_device.py
```
- Sets script owner

```bash
chmod 750 /opt/zabbix/tuya/tuya_device.py
```
- Owner: full access  
- Group: read + execute  
- Others: no access  

---

## 🔗 Step 6: Link Script to Zabbix

```bash
ln -s /opt/zabbix/tuya/tuya_device.py /usr/lib/zabbix/externalscripts/tuya_device.py
```
- Creates symbolic link in Zabbix scripts directory

```bash
chown -h zabbix:zabbix /usr/lib/zabbix/externalscripts/tuya_device.py
```
- Ensures Zabbix can execute the script

---

## 🧪 Step 7: Test Script

```bash
source /opt/zabbix/tuya/venv/bin/activate
python3 /opt/zabbix/tuya/tuya_device.py
```

Example output:

```json
{"switch_1": 1, "power_w": 17.2, "voltage_v": 234.2, "current_a": 0.198, "energy_delta_kwh": 0.361}
```

---

## 📡 Step 8: Zabbix Configuration

### ➤ Create Host (without interface)

<img src="https://github.com/user-attachments/assets/1bb8bc73-f43e-403f-a40e-2e505d47cbc2" />

---

### ➤ Master Item

- Executes the script
- Returns full JSON

<img src="https://github.com/user-attachments/assets/43137332-d49d-44af-84ee-450070ece8a1" />

---

### ➤ Dependent Items

Example: power consumption

<img src="https://github.com/user-attachments/assets/2ef4938e-ea5f-401c-aa92-f055707a52da" />

---

### ➤ Preprocessing

Use JSONPath to extract values

<img src="https://github.com/user-attachments/assets/9e21e77e-694c-4a12-9e30-5778047e5074" />

---

## ✅ Final Result

<img width="1152" height="214" alt="image" src="https://github.com/user-attachments/assets/161a54d3-66ad-42a0-825a-f1f4cde96e0c" />

<img width="1918" height="693" alt="image" src="https://github.com/user-attachments/assets/49487329-5a93-45c7-88de-1db2599841d3" />


- Real-time monitoring
- Daily energy usage (kWh)
- Clean integration with Zabbix

---

## 🚀 Notes

- Tuya API returns energy in **Wh**
- Script converts to **kWh**
- Values match Tuya app (rounded)

---

## 📜 License

MIT
