import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import json
from getmac import get_mac_address
from datetime import datetime
from requests import get
import subprocess



# MQTT
MQTT_HOST = "raspberrypiaidbroker"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 5
MQTT_TOPIC = "button"

# GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# MQTT
mqttc = mqtt.Client()

#ONLINE/OFFLINE handling
is_connected = False
offline_survey_collection = []

# MQTT callbacks
def on_connect(mosq, obj, rc, properties=None):
    print("🎉Connected to MQTT Broker!")
    global is_connected
    is_connected = True

def on_publish(client, userdata, mid):
    print("Message Published...")

def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT Broker!")
    global is_connected
    is_connected = False

# MQTT callbacks
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_disconnect = on_disconnect

# MQTT connect
mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

# MQTT loop
mqttc.loop_start()


# MAC address
mac_address = get_mac_address()

# Get Created devices
def get_created_devices():
    url = "http://raspberrypiaidbroker:8000/devices"
    created_devices = get(url).text
    return created_devices
  

#Create Device if it does not exist:
def create_device():
    created_devices = get_created_devices()
    if mac_address in created_devices: #Check if this device is already in the server
        pass
    else:
        MQTT_TOPIC = "createDevice"

        payload={}
        payload['deviceId'] = mac_address
        payload['location'] = get_wifi_strenght()
        payload = json.dumps(payload)
        mqttc.publish(MQTT_TOPIC, payload)

#Wifi Strengh for location
def get_wifi_strenght():
    wifi_strenght = subprocess.getoutput("sudo iwlist  scan | grep -e ESSID -e level")

    wifi_strenght = wifi_strenght.split("\n", 1)[1]
    wifi_strenght = wifi_strenght.split("\n", 1)[1]
    wifi_strenght = wifi_strenght.split("\n", 1)[1]
    wifi_strenght = wifi_strenght.split("\n", 1)[1]
    wifi_strenght = wifi_strenght.replace("  ","")

    wifi_strenght_list = []
    for line in wifi_strenght.splitlines():
        wifi_strenght_list.append(line)

    wifi_strenght_string = wifi_strenght_list[1] + wifi_strenght_list[0]
    return wifi_strenght_string

#location
last_available_location = ""
def get_location(device_id):

    mac_address = device_id
    url = "http://raspberrypiaidbroker:8000/devices/{}/location".format(mac_address)
    if is_connected:
        try:
            location = get(url).text[1:-1]#need to remove the first and last character '" "'
            global last_available_location
            last_available_location = location
            return location
        except:
            return last_available_location
    else:
        return last_available_location


#Post Survey
def post_survey(button):
    MQTT_TOPIC = "createSatisfaction"

    payload={}
    payload['satisfaction']=button
    payload['deviceId'] = mac_address
    payload['insertedAt'] = datetime.now().isoformat()
    payload['location'] = get_location(mac_address)
    
    payload = json.dumps(payload)
    if is_connected==True:
        mqttc.publish(MQTT_TOPIC, payload)
        #we are going to send the surveys we collected while we were offline (if we were)
        for offline_survey in offline_survey_collection:
            mqttc.publish(MQTT_TOPIC, offline_survey)
        offline_survey_collection.clear()
    elif is_connected==False:
        offline_survey_collection.append(payload)
        print(offline_survey_collection)



create_device() # it will add this device to our DB in case it is not here already


# GPIO loop
while True:
    if GPIO.input(17) == False:
        print("happy pressed")
        post_survey("happy")
        time.sleep(3)
    if GPIO.input(27) == False:
        print("neutral pressed")
        post_survey("neutral")
        time.sleep(3)
    if GPIO.input(22) == False:
        print("sad pressed")
        post_survey("sad")
        time.sleep(3)
