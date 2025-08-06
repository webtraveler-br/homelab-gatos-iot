import paho.mqtt.client as mqtt

BROKER = "192.168.1.67"
PORT = 1883
TOPIC = "sensors/nodes/table_presence"

def on_message(client, userdata, message):
    print(f"Recebido no tópico '{message.topic}': {str(message.payload.decode('utf-8'))}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao Broker!")
        client.subscribe(TOPIC)
    else:
        print(f"Falha na conexão, código {rc}")

client = mqtt.Client(client_id="mqtt_test_script")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

print("Aguardando mensagens...")
client.loop_forever()
