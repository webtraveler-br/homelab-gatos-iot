from flask import Flask, jsonify
from libs.mqtt_client import MQTTClient
from libs.env_utils import get_env_vars
from libs.log_utils import setup_logging
import logging

app = Flask(__name__)

file_handler = setup_logging("command_gateway", log_dir="/app/logs")

required_vars = ["MQTT_BROKER_HOST", "MQTT_BROKER_PORT"]
config = get_env_vars(required_vars, logger=file_handler)

mqtt_client = MQTTClient(
    broker_host=config["MQTT_BROKER_HOST"],
    broker_port=int(config["MQTT_BROKER_PORT"]),
    logger=file_handler,
)
mqtt_client.connect()


@app.route("/commands/buzzer", methods=["POST"])
def handle_table_alarm():
    topic = "commands/nodes/table_presence"
    payload = '{"action": "buzzer"}'
    
    try:
        mqtt_client.publish(topic, payload)
        logging.info(f"Comando enviado para {topic}: {payload}")
        return jsonify({"status": "Comando enviado"}), 200
    except Exception as e:
        logging.error(f"Erro ao enviar comando: {e}", exc_info=True)
        return jsonify({"status": "Falha ao enviar comando"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
