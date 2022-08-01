from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from requests import request
from sqlmodel import Session, select
import json
from fastapi.templating import Jinja2Templates
import uvicorn

from fastapi_mqtt.fastmqtt import FastMQTT
from fastapi_mqtt.config import MQTTConfig

import sqlmodel


from datetime import datetime
import json


from models.device import Device, Satisfaction, create_db_and_tables

app = FastAPI()

#Section
mqtt_config = MQTTConfig()
mqtt = FastMQTT(config=mqtt_config)
mqtt.init_app(app)

@mqtt.on_connect()
def connect(client, flags, rc, properties):
    mqtt.client.subscribe("createDevice")
    mqtt.client.subscribe("createSatisfaction")
    print("Connected: ", client, flags, rc, properties)



@app.on_event("startup") #this happens only once
def on_startup():
    global engine
    engine = create_db_and_tables()
    now = datetime.now()


templates = Jinja2Templates(directory="templates")


def getDevices():
    with Session(engine) as session:
        devices = session.exec(select(Device)).all()
        return devices

def getDeviceById(deviceId):
    with Session(engine) as session:
        device = session.exec(select(Device).where(
            Device.deviceId == deviceId)).first()
        return device

def createDevice(device: Device):
    with Session(engine) as session:
        session.add(device)
        session.commit()
        return device

def createSatisfaction(satisfaction: Satisfaction):
    with Session(engine) as session:
        session.add(satisfaction)
        session.commit()
        return satisfaction

# Website Section

@app.get("/")
def read_root(request: Request):
    devices = getDevices()
    # get index.html / pass devices to it and run the dynamic python code inside the html / and return the html to the client
    return templates.TemplateResponse("index.html", {"request": request, "devices": devices}) #ninja needs access to the request

@app.get("/devices/{deviceId}")
def read_root(request: Request, deviceId):
    devices = getDevices()
    satisfactions = [s.toJSON() for s in getSatisfactions(deviceId) ]
    return templates.TemplateResponse("device.html", {"request": request, "devices": devices, "satisfactions": satisfactions})


# API section


@app.get("/devices")
def listDevices():
    return getDevices()


@app.get("/devices/{deviceId}/location")
def getLocation(deviceId: str):
    with Session(engine) as session:
        device = session.exec(select(Device).where(
            Device.deviceId == deviceId)).first()
        return device.location


@app.get("/devices/{deviceId}/satisfactions")
def getSatisfactions(deviceId: str):
    with Session(engine) as session:
        device = session.exec(select(Device).where(
            Device.deviceId == deviceId)).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        satisfactions = session.exec(select(Satisfaction).where(
            Satisfaction.deviceId == deviceId)).all()
        return satisfactions


@mqtt.on_message()
async def handleMessage(client, topic, payload, qos, properties):
    decodedPayload = json.loads(payload.decode())
    if topic == "createDevice":
        device = Device(
            deviceId=decodedPayload.get('deviceId'),
            location=decodedPayload.get('location')
            )
        createDevice(device)
    elif topic == "createSatisfaction":
        satisfaction = Satisfaction(
            satisfaction=decodedPayload.get('satisfaction'),
            insertedAt=decodedPayload.get('insertedAt'),
            deviceId=decodedPayload.get('deviceId'),
            location=decodedPayload.get('location'),
            comment=decodedPayload.get('comment')
        )
        createSatisfaction(satisfaction)


@app.post("/satisfactions") #for python sending json
def createSatisfactionAPI(satisfaction: Satisfaction):
    newSatisfaction = createSatisfaction(satisfaction)
    return newSatisfaction

@app.post("/devices/{deviceId}", response_class=RedirectResponse, status_code=302) #redirect to "/" page
def updateDevice(deviceId: str, location: str = Form()):
    print(location, deviceId)
    with Session(engine) as session:
        device = session.exec(select(Device).where(
            Device.deviceId == deviceId)).first()
        device.location = location
        session.commit()
        return "/"

#website graphical interface for collecting surveys (survey.html)
@app.get("/devices/{deviceId}/survey")
def read_root(request: Request, deviceId):
    device = getDeviceById(deviceId)
    satisfactions = getSatisfactions(deviceId)
    return templates.TemplateResponse("survey.html", {"request": request, "device": device, "satisfactions": satisfactions})


@app.post("/satisfactions/{deviceId}", response_class=RedirectResponse, status_code=302)
def createSatisfactionWeb(deviceId: str, satisfaction: str = Form(), time: str = Form(), comment = Form(default="")):
   
    category = "whoknows"#openAI.get_category(comment) # here

    satisfactionRecord = Satisfaction(deviceId=deviceId, satisfaction= satisfaction, insertedAt=time, comment=comment, category=category)
    with Session(engine) as session:
        session.add(satisfactionRecord)
        session.commit()

    url = "/devices/{}/survey".format(deviceId)
    return url
    #satisfaction.category = openAI_getcategory(satisfaction.comment)
    # with Session(engine) as session:
    #     session.add(satisfaction)
    #     session.commit()
    #     return satisfaction



if __name__ == "__main__":
    uvicorn.run("main:app", log_level="info")