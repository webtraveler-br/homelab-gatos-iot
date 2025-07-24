import paho.mqtt.client as mqtt
import sys
import argparse
import json
from sensor_logs import SensorLogsDB

# argumentos e menu de ajuda
parser = argparse.ArgumentParser(
    description="Script para persistência dos dados dos sensores",
    add_help=False
)
parser.add_argument('-h', '--help', action='help', help='Mostra essa mensagem de ajuda')
parser.add_argument('-b', '--broker', type=str, help='Endereço do broker MQTT')
parser.add_argument('-p', '--port', type=int, default=1883, help='Porta do broker MQTT (padrão 1883)')

# carrega os argumentos para conectar ao MQTT (IP varia, porta provavelmente não)
args = parser.parse_args()

# conecta ao banco de dados
db = SensorLogsDB()

def main():
    broker = args.broker
    port = args.port

    db.create_table()

    client = mqtt.Client(client_id="cat_ingestor_app")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker, port, 60)
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
    
    db.insert_log(message.topic, mqtt_message_json)
    print(f"Recebido no tópico '{message.topic}': {mqtt_message_str}")

def on_connect(client, userdata, flags, rc):
    topic = "sensores/nodes/#"
    if rc == 0:
        print("Conectado ao Broker!")
        client.subscribe(topic)
    else:
        print(f"Falha na conexão, código {rc}")

main()