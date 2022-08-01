import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import json
from getmac import get_mac_address
from datetime import datetime
from requests import get

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
    #we are going to send the surveys we collected while we were offline
    for offline_survey in offline_survey_collection:
        mqttc.publish(MQTT_TOPIC, offline_survey)
    offline_survey_collection.clear()
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

#location
def get_location(device_id):
    mac_address = device_id
    url = "http://raspberrypiaidbroker:8000/devices/{}/location".format(mac_address)
    location = get(url).text[1:-1]#need to remove the first and last character '" "'
    return location
#Post Survey
def post_survey(survey):
    payload={}
    payload['satisfaction']=survey
    payload['deviceId'] = get_mac_address()
    payload['insertedAt'] = datetime.now().isoformat()
    payload['location'] = get_location(get_mac_address())
    
    
    payload = json.dumps(payload)
    if is_connected:
        mqttc.publish(MQTT_TOPIC, payload)
    else:
        offline_survey_collection.append(survey)

# GPIO loop
while True:
    if is_connected == True:
        if GPIO.input(17) == False:
            print("Button 17 pressed")
            mqttc.publish(MQTT_TOPIC, json.dumps({"button": "17"}))
            time.sleep(3)
        if GPIO.input(27) == False:
            print("Button 27 pressed")
            mqttc.publish(MQTT_TOPIC, json.dumps({"button": "27"}))
            time.sleep(3)
        if GPIO.input(22) == False:
            print("Button 22 pressed")
            mqttc.publish(MQTT_TOPIC, json.dumps({"button": "22"}))
            time.sleep(3)
    
    elif is_connected == False:
        if GPIO.input(17) == False:
            print("Button 17 pressed")
            offline_survey_collection.append(json.dumps({"button":"17"}))
            print(offline_survey_collection)
            time.sleep(3)
        if GPIO.input(27) == False:
            print("Button 27 pressed")
            offline_survey_collection.append(json.dumps({"button":"27"}))
            time.sleep(3)
        if GPIO.input(22) == False:
            print("Button 22 pressed")
            offline_survey_collection.append(json.dumps({"button":"22"}))
            time.sleep(3)