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
