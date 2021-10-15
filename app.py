import paho.mqtt.client as mqtt
import json
import time

from flask import Flask
from flask import render_template

app = Flask(__name__)

DELAY = 1  # longer delays may improve performance and use less data
USERNAME = "kkelso"
PASSWORD = "hiveMQ!23"
# HOST = "74a454df0d3ed456fbfb6a3d1ed57b14f.s1.eu.hivemq.cloud"
HOST = "f3edf0f5f7094a11a477cfb3f6519446.s1.eu.hivemq.cloud"
PORT = 8883

topics = 'Warehouse Truck Site'.split()
debug_topic = 'debug'

serial_numbers = '255043926169824 59910660233440 104608418437344 10643107158240 110032962132192 126796219488480 146084900837600 156135141087456 16321053923552 163612645595360 205673293879520 216187357042912 220254691072224 251869962115296 252239312525536 257779820337376 259283058890976 260099102677216 268160756291808 270394139285728 277077125175520 279203100432608 29811562977504 33664115087584 40819547379936 41291993782496 43280563640544 44388681980128 50556238239968 50813936277728 53064499140832 6000247511264 60043804219616 63106132678880 70523557976288 97324137126112'.split()
mac_addresses = []
# {"DeviceName":"N/A","DeviceMAC":"E0:18:9F:09:7D:36","DeviceRSSI":-50}
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

    for mac in mac_addresses:
        warehouse_beacons[mac] = -999
        truck_beacons[mac] = -999
        site_beacons[mac] = -999


def on_connect(client, userdata, flags, rc):
    init_beacons()
    for topic in topics:
        client.subscribe(topic)
        client.publish(debug_topic, f'Subscribed to {topic}')

    client.publish(debug_topic, "STARTING SERVER")
    client.publish(debug_topic, "CONNECTED")


def validate_data(data):
    if 'DeviceMAC' not in data.keys():
        return False

    if 'DeviceRSSI' not in data.keys():
        return False

    if data['DeviceMAC'].lower() not in warehouse_beacons.keys():
        return False

    return True


def update_devices():
    devices['warehouse'] = 0
    devices['truck'] = 0
    devices['site'] = 0

    for mac in mac_addresses:
        warehouse_signal = warehouse_beacons[mac]
        truck_signal = truck_beacons[mac]
        site_signal = site_beacons[mac]
        if warehouse_signal == -999 and truck_signal == -999 and site_signal == -999:
            continue

        if warehouse_signal == max(warehouse_signal, truck_signal, site_signal):
            devices['warehouse'] += 1
            continue
        if truck_signal == max(warehouse_signal, truck_signal, site_signal):
            devices['truck'] += 1
            continue
        if site_signal == max(warehouse_signal, truck_signal, site_signal):
            devices['site'] += 1
            continue


def on_message(client, userdata, msg):
    client.publish(debug_topic, 'Unknown topic')


def on_topic_msg(topic, beacons, client, userdata, msg):
    client.publish(debug_topic, f'{topic}: msg: {msg.payload.decode()}')
    data = json.loads(msg.payload.decode())

    if not validate_data(data):
        client.publish(debug_topic, 'invalid data')
        return

    beacons[data['DeviceMAC'].lower()] = int(data['DeviceRSSI'])
    client.publish(debug_topic, f'{topic} updated')

    update_devices()
    time.sleep(DELAY)


def on_warehouse_msg(client, userdata, msg):
    on_topic_msg('Warehouse', warehouse_beacons, client, userdata, msg)


def on_truck_msg(client, userdata, msg):
    on_topic_msg('Truck', truck_beacons, client, userdata, msg)


def on_site_msg(client, userdata, msg):
    on_topic_msg('Site', site_beacons, client, userdata, msg)


@app.route("/")
def home():
    return render_template("home.html", name="home", devices=devices,
                           warehouse_beacons=warehouse_beacons,
                           truck_beacons=truck_beacons,
                           site_beacons=site_beacons)


client = mqtt.Client()
client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.message_callback_add('Warehouse', on_warehouse_msg)
client.message_callback_add('Truck', on_truck_msg)
client.message_callback_add('Site', on_site_msg)
client.connect(HOST, PORT)
client.loop_start()

if __name__ == "__main__":
    app.run(debug=True)
