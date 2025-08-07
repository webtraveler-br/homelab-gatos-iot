from libs.mqtt_client import MQTTClient
from libs.rabbitmq_client import RabbitMQClient
from libs.env_utils import get_env_vars
from libs.log_utils import setup_logging
import json
import logging
from typing import Any, Dict

# Serviço de análise de toxicidade para mq-135 do homelab.
# Recebe mensagens MQTT, analisa toxicidade e publica alertas no RabbitMQ.

CLIENT_ID = "analysis_agent_anomaly"
HIGH_SEVERITY = "HIGH"
TOXICITY_BASELINE = 1400
TOXICITY_THRESHOLD = 300

# Configuração de logging
file_handler = setup_logging(CLIENT_ID, log_dir="/app/logs")


# Handler chamado ao receber mensagem MQTT.
# Se toxicidade estiver acima do limite, publica alerta no RabbitMQ.

def on_message(client: Any, userdata: Dict[str, Any], message: Any) -> None:
    topic = message.topic
    mqtt_message_str = message.payload.decode("utf-8")

    try:
        mqtt_message_json = json.loads(mqtt_message_str)

        if int(mqtt_message_json["toxicity"]) > TOXICITY_BASELINE + TOXICITY_THRESHOLD:
            userdata["rabbitmq"].publish(
                CLIENT_ID,
                HIGH_SEVERITY,
                "Niveis de toxicidade altos!",
                topic,
                mqtt_message_json["toxicity"],
                userdata["queue"],
            )
            logging.info(f"Insight gerado e enviado ao RabbitMQ")

    except json.JSONDecodeError as decode_err:
        logging.error(f"Payload não é um JSON válido. Análise inviável. Payload: {mqtt_message_str}")
    except Exception as e:
        logging.error(f"Erro inesperado ao decodificar mensagem MQTT: {e}", exc_info=True)


# Função principal do serviço. Inicializa configs, MQTT, RabbitMQ e inicia o loop.
def main() -> None:
    required_vars = [
        "MQTT_BROKER_HOST",
        "MQTT_BROKER_PORT",
        "MQTT_TOPIC",
        "RABBITMQ_HOST",
        "RABBITMQ_PORT",
        "RABBITMQ_QUEUE",
        "RABBITMQ_USER",
        "RABBITMQ_PASSWORD",
    ]

    rabbitmq_client = None
    mqtt_client = None

    try:
        config = get_env_vars(required_vars, logger=file_handler)

        rabbitmq_client = RabbitMQClient(
            config["RABBITMQ_USER"], config["RABBITMQ_PASSWORD"], config["RABBITMQ_HOST"], config["RABBITMQ_PORT"]
        )
        logging.info("Cliente RabbitMQ configurado.")

        mqtt_client = MQTTClient(
            broker_host=config["MQTT_BROKER_HOST"],
            broker_port=config["MQTT_BROKER_PORT"],
            topic=config["MQTT_TOPIC"],
            on_message=on_message,
            logger=file_handler,
            client_id=CLIENT_ID,
            userdata={"rabbitmq": rabbitmq_client, "queue": config["RABBITMQ_QUEUE"]},
        )
        mqtt_client.connect_and_listen()

    except KeyboardInterrupt:
        logging.info("Aplicação encerrada pelo usuário.")
    except (ValueError, Exception) as e:
        logging.critical(f"Erro crítico inesperado na aplicação: {e}", exc_info=True)
    finally:
        if mqtt_client:
            mqtt_client.disconnect()


if __name__ == "__main__":
    main()
