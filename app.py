import paho.mqtt.client as mqtt
import json
import time

from flask import Flask, jsonify, render_template

app = Flask(__name__)

DELAY = 2  # longer delays may improve performance and use less data
USERNAME = "kkelso"
PASSWORD = "hiveMQ!23"
HOST = "f3edf0f5f7094a11a477cfb3f6519446.s1.eu.hivemq.cloud"
PORT = 8883

topics = 'Warehouse Truck Site'.split()
debug_topic = 'debug'

serial_numbers = '255043926169824 59910660233440 104608418437344 10643107158240 110032962132192 126796219488480 146084900837600 156135141087456 16321053923552 163612645595360 205673293879520 216187357042912 220254691072224 251869962115296 252239312525536 257779820337376 259283058890976 260099102677216 268160756291808 270394139285728 277077125175520 279203100432608 29811562977504 33664115087584 40819547379936 41291993782496 43280563640544 44388681980128 50556238239968 50813936277728 53064499140832 6000247511264 60043804219616 63106132678880 70523557976288 97324137126112'.split()
mac_addresses = []
# {"DeviceName":"N/A","DeviceMAC":"E0:18:9F:09:7D:36","DeviceRSSI":-50}
locations = {'warehouse': 0, 'truck': 0, 'site': 0}
beacons = {}
MAX_TTL = 10
# beacons -> {"<mac>": {"site": [<rssi>, <ttl>], "warehouse": [<rssi>, <ttl>], "truck": [<rssi>, <ttl>]}}
# beacons -> {"<some mac address>": [<RSSI>, <location>, <ttl>]}


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
        beacons[mac] = {"site": [-999, 0],
                        "warehouse": [-999, 0],
                        "truck": [-999, 0]}


def on_connect(client, userdata, flags, rc):
    init_beacons()
    for topic in topics:
        client.subscribe(topic)
        client.publish(debug_topic, f'Subscribed to {topic}')

    client.publish(debug_topic, "STARTING SERVER")


def validate_data(data):
    if 'DeviceMAC' not in data.keys():
        return 'missing mac address'

    if 'DeviceRSSI' not in data.keys():
        return 'missing rssi'

    if data['DeviceMAC'].lower() not in beacons.keys():
        return 'unrecognized mac'

    try:
        int(data['DeviceRSSI'])
    except:
        return 'invalid rssi'

    return None


def expire_ttls(beacon_info):
    for location in beacon_info.keys():
        beacon_info[location][1] -= 1

        loc_info = beacon_info[location]
        ttl = loc_info[1]
        if ttl <= 0:
            loc_info[0] = -999
            loc_info[1] = 0
            beacon_info[location] = loc_info

    return beacon_info


def update_devices():
    locations['warehouse'] = 0
    locations['truck'] = 0
    locations['site'] = 0

    for mac in mac_addresses:
        beacon_info = beacons[mac]

        # decrement ttl's
        beacon_info = expire_ttls(beacon_info)

        max_rssi = -999
        max_loc = ''
        for loc in beacon_info.keys():
            rssi = beacon_info[loc][0]
            if rssi > max_rssi:
                max_rssi = rssi
                max_loc = loc

        if max_rssi != -999 and max_loc != '':
            locations[max_loc] += 1


def on_message(client, userdata, msg):
    client.publish(debug_topic, 'Unknown topic')


def on_topic_msg(topic, client, userdata, msg):
    data = json.loads(msg.payload.decode())

    valid_msg = validate_data(data)
    if valid_msg:
        if 'unrecognized' in valid_msg:
            return
        client.publish(debug_topic, f'{topic}: invalid data, {valid_msg}')
        return

    mac = data['DeviceMAC'].lower()
    rssi = int(data['DeviceRSSI'])
    location = topic.lower()
    client.publish(debug_topic, f'{location},{mac.split(":")[-1]},{rssi}')

    beacon_info = beacons[mac]
    beacon_info[location] = [rssi, MAX_TTL]
    beacons[mac] = beacon_info

    update_devices()
    time.sleep(DELAY)


def on_warehouse_msg(client, userdata, msg):
    on_topic_msg('Warehouse', client, userdata, msg)


def on_truck_msg(client, userdata, msg):
    on_topic_msg('Truck', client, userdata, msg)


def on_site_msg(client, userdata, msg):
    on_topic_msg('Site', client, userdata, msg)


@app.route('/_stuff', methods=['GET'])
def stuff():
    return jsonify(beacons)


@app.route("/")
def home():
    return render_template("home.html", name="home", locations=locations,
                           beacons=beacons)


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
    debug_topic = "local_debug"
    app.run(debug=True)
