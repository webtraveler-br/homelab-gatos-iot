import paho.mqtt.client as mqtt
import sys
import json
import os
from sensor_logs import SensorLogsDB

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensores/nodes/#")
MQTT_CLIENT_ID = "cat_ingestor_app"

DB_PARAMS = {
    'dbname': os.getenv("POSTGRES_DB"),
    'user': os.getenv("POSTGRES_USER"),
    'password': os.getenv("POSTGRES_PASSWORD"),
    'host': os.getenv("POSTGRES_HOST", "localhost")
}

# conecta ao banco de dados
db = SensorLogsDB(DB_PARAMS)

def main():
    db.create_table()

    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    except Exception as e:
        print(f"Erro ao conectar ao broker MQTT: {e}")
        db.close()
        sys.exit(1)

    print("Aguardando mensagens...")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Encerrando por interrupção do usuário.")
        db.close()
        sys.exit(0)
    except Exception as e:
        print(f"Erro inesperado no loop MQTT: {e}")
        db.close()
        sys.exit(1)

# inserção da mensagem no db
def on_message(client, userdata, message):
    mqtt_message_str = message.payload.decode('utf-8')
    try:
        mqtt_message_json = json.loads(mqtt_message_str)
    except Exception:
        mqtt_message_json = {"raw": mqtt_message_str} # não deveria haver problema com formatação, mas caso haja...
    
    db.insert_log(message.topic, json.dumps(mqtt_message_json))
    print(f"Recebido no tópico '{message.topic}': {mqtt_message_str}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao Broker!")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Falha na conexão, código {rc}")

main()