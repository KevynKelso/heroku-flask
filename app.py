import paho.mqtt.client as mqtt

from flask import Flask
from flask import render_template

app = Flask(__name__)

USERNAME="kkelso"
PASSWORD="hiveMQ!23"
HOST="74a454df0d3ed456fbfb6a3d1ed57b14f.s1.eu.hivemq.cloud"
PORT=8883

topics = 'Warehouse Truck Site'.split()
debug_topic = 'debug'

# {"DeviceName":"N/A","DeviceMAC":"E0:18:9F:09:7D:36","DeviceRSSI":-50}
data = {}
devices = {'warehouse': 0, 'truck': 0, 'site': 0}

def on_connect(client, userdata, flags, rc):
    for topic in topics:
        client.subscribe(topic)

    client.publish('debug', "STARTING SERVER")
    client.publish('debug', "CONNECTED")


def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    client.publish('debug', "RECIEVED")


@app.route("/")
def home():
    return render_template("home.html", name="home", data=data, devices=devices)

client = mqtt.Client()
client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.connect(HOST, PORT)
client.loop_start()

if __name__ == "__main__":
    app.run(debug=True)
