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



The command to change the script permissions to block access for the rest of the system:
chown tuya:tuya /opt/zabbix/tuya/tuya_device.py
chmod 750 /opt/zabbix/tuya/tuya_device.py




ln -s /opt/zabbix/tuya/tuya_device.py /usr/lib/zabbix/externalscripts/tuya_device.py
chown -h zabbix:zabbix /usr/lib/zabbix/externalscripts/tuya_device.py

Create a script link in the Zabbix directory and set the link owner to the zabbix user so that Zabbix can see and run the script from the correct location:
ln -s /opt/zabbix/tuya/tuya_device.py /usr/lib/zabbix/externalscripts/tuya_device.py
chown -h zabbix:zabbix /usr/lib/zabbix/externalscripts/tuya_device.py

Test what the script returns:

Adding a Host - without an interface. Data will be collected from the "Master Item" value added
<img width="1047" height="558" alt="image" src="https://github.com/user-attachments/assets/1bb8bc73-f43e-403f-a40e-2e505d47cbc2" />

Master Item, which runs through the entire script and will be used to display other data of interest to us.
<img width="1045" height="727" alt="image" src="https://github.com/user-attachments/assets/43137332-d49d-44af-84ee-450070ece8a1" />


Adding Item for current power consumption:

<img width="1042" height="677" alt="image" src="https://github.com/user-attachments/assets/2ef4938e-ea5f-401c-aa92-f055707a52da" />

Preprocessing tab, to specify what should be read from the script.
<img width="1048" height="276" alt="image" src="https://github.com/user-attachments/assets/9e21e77e-694c-4a12-9e30-5778047e5074" />

