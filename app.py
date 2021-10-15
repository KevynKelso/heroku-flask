import paho.mqtt.client as mqtt
import json

from flask import Flask
from flask import render_template

app = Flask(__name__)

USERNAME = "kkelso"
PASSWORD = "hiveMQ!23"
# HOST = "74a454df0d3ed456fbfb6a3d1ed57b14f.s1.eu.hivemq.cloud"
HOST = "f3edf0f5f7094a11a477cfb3f6519446.s1.eu.hivemq.cloud"
PORT = 8883

topics = 'Warehouse Truck Site'.split()
debug_topic = 'debug'

serial_numbers = '104608418437344 10643107158240 110032962132192 126796219488480 146084900837600 156135141087456 16321053923552 163612645595360 205673293879520 216187357042912 220254691072224 251869962115296 252239312525536 257779820337376 259283058890976 260099102677216 268160756291808 270394139285728 277077125175520 279203100432608 29811562977504 33664115087584 40819547379936 41291993782496 43280563640544 44388681980128 50556238239968 50813936277728 53064499140832 6000247511264 60043804219616 63106132678880 70523557976288 97324137126112'.split()
mac_addresses = []
# {"DeviceName":"N/A","DeviceMAC":"E0:18:9F:09:7D:36","DeviceRSSI":-50}
# is DeviceName = Warehouse | truck | site ?
devices = {'warehouse': 0, 'truck': 0, 'site': 0}
warehouse_beacons = {}
truck_beacons = {}
site_beacons = {}


def sn_to_bytes(sn: int) -> str:
    temp = hex(int.from_bytes(sn.to_bytes(6, 'little'), 'big'))[2:]
    returnValue = temp[:2]
    for i in range(1, int(len(temp)/2)):
        returnValue += f':{temp[2*i:2*i+2]}'

    return returnValue


def init_beacons():
    for sn in serial_numbers:
        mac = sn_to_bytes(int(sn))
        if mac not in mac_addresses:
            mac_addresses.append(mac)

        warehouse_beacons[mac] = 0
        truck_beacons[mac] = 0
        site_beacons[mac] = 0


def on_connect(client, userdata, flags, rc):
    init_beacons()
    for topic in topics:
        client.subscribe(topic)
        client.publish(debug_topic, f'Subscribed to {topic}')

    client.publish(debug_topic, "STARTING SERVER")
    client.publish(debug_topic, "CONNECTED")


def validate_data(data):
    if 'DeviceMAC' not in data.keys() or 'DeviceName' not in data.keys():
        return False

    if 'DeviceRSSI' not in data.keys():
        return False

    if data['DeviceMAC'].lower() not in warehouse_beacons.keys():
        return False

    return True


def on_message(client, userdata, msg):
    client.publish(debug_topic, msg.payload.decode())
    data = json.loads(msg.payload.decode())

    if not validate_data(data):
        client.publish(debug_topic, 'invalid data')
        return

    if data['DeviceName'].lower() == 'warehouse':
        warehouse_beacons[data['DeviceMAC'].lower()] = abs(
            int(data['DeviceRSSI']))
        client.publish(debug_topic, 'warehouse updated')

    if data['DeviceName'].lower() == 'truck':
        truck_beacons[data['DeviceMAC'].lower()] = abs(int(data['DeviceRSSI']))
        client.publish(debug_topic, 'truck updated')

    if data['DeviceName'].lower() == 'site':
        site_beacons[data['DeviceMAC'].lower()] = abs(int(data['DeviceRSSI']))
        client.publish(debug_topic, 'site updated')


@app.route("/")
def home():
    return render_template("home.html", name="home", devices=devices, beacons=warehouse_beacons)


client = mqtt.Client()
client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.connect(HOST, PORT)
client.loop_start()

if __name__ == "__main__":
    app.run(debug=True)
