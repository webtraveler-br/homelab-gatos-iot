from libs.mqtt_client import MQTTClient
from libs.ingestor_db import IngestorDB
from libs.rabbitmq_client import RabbitMQClient
from libs.env_utils import get_env_vars
from libs.log_utils import setup_logging
import sys
import json
import logging
import threading
from functools import partial
from typing import Any, Dict

CLIENT_ID = "cat_ingestor"

# Serviço de ingestão de dados de sensores do homelab.
# Recebe mensagens MQTT, valida e insere logs no banco PostgreSQL.

# Configuração de logging para arquivo e console
file_handler = setup_logging(CLIENT_ID, log_dir="/app/logs")


# Handler chamado ao receber mensagem MQTT.
# Insere o log no banco, mesmo se o payload não for JSON válido.
def on_mqtt_message(client: Any, userdata: Dict[str, Any], message: Any) -> None:
    db = userdata["db"]
    topic = message.topic
    mqtt_message_str = message.payload.decode("utf-8")
    logging.info(f"Mensagem recebida no tópico '{topic}': {mqtt_message_str}")

    try:
        mqtt_message_json = json.loads(mqtt_message_str)
    except json.JSONDecodeError as decode_err:
        logging.warning(f"Payload não é um JSON válido. Inserindo como texto. Payload: {mqtt_message_str}")
        mqtt_message_json = {"raw": mqtt_message_str}
    except Exception as e:
        logging.error(f"Erro inesperado ao decodificar mensagem MQTT: {e}", exc_info=True)
        mqtt_message_json = {"raw": mqtt_message_str}

    db.insert_log(topic, json.dumps(mqtt_message_json))
    logging.info(f"Mensagem do tópico '{topic}' inserida no banco de dados.")


# Handler chamado ao receber mensagem RabbitMQ.
# Insere o log no banco, mesmo se o payload não for JSON válido.
def on_rabbitmq_message(
    channel: Any, method: Any, properties: Any, body: bytes, db: Any, config: Dict[str, Any]
) -> None:
    rabbitmq_message_str = body.decode("utf-8")
    topic = method.routing_key
    logging.info(f"Mensagem recebida na fila '{topic}': {rabbitmq_message_str}")

    try:
        rabbitmq_message_json = json.loads(rabbitmq_message_str)
        db.insert_insight(
            rabbitmq_message_json["type"], rabbitmq_message_json["severity"], json.dumps(rabbitmq_message_json)
        )
        logging.info(f"Mensagem da fila '{topic}' inserida no banco de dados.")
    except (Exception, json.JSONDecodeError) as e:
        logging.error(f"Erro inesperado ao decodificar mensagem RabbitMQ: {e}", exc_info=True)


# Função que inicializa o ingestão MQTT, conecta ao banco, garante tabela e processa mensagens enquanto não houver shutdown.
def mqtt_ingestor(db_params: Dict[str, Any], config: Dict[str, Any], shutdown_event: threading.Event) -> None:
    global file_handler
    db = None
    mqtt_client = None

    try:
        db = IngestorDB(db_params, file_handler)
        db.create_sensor_logs_table()
        logging.info("Conexão com o banco de dados estabelecida e tabela garantida.")

        client_userdata = {"db": db, "config": config}
        mqtt_client = MQTTClient(
            broker_host=config["MQTT_BROKER_HOST"],
            broker_port=config["MQTT_BROKER_PORT"],
            topic=config["MQTT_TOPIC"],
            on_message=on_mqtt_message,
            logger=file_handler,
            client_id=CLIENT_ID,
            userdata=client_userdata,
        )
        # Loop principal com verificação do shutdown_event
        while not shutdown_event.is_set():
            mqtt_client.connect_and_listen(timeout=1)

    except KeyboardInterrupt:
        logging.info("Aplicação encerrada pelo usuário.")
    except Exception as e:
        logging.critical(f"Erro crítico inesperado na aplicação: {e}", exc_info=True)
    finally:
        if mqtt_client:
            mqtt_client.disconnect()
        if db:
            try:
                db.close()
                logging.info("Conexão com o banco de dados fechada.")
            except Exception as close_err:
                logging.error(f"Erro ao fechar conexão com o banco: {close_err}", exc_info=True)


# Função que inicializa o ingestão RabbitMQ, conecta ao banco, garante tabela e processa mensagens enquanto não houver shutdown.
def rabbitmq_ingestor(db_params: Dict[str, Any], config: Dict[str, Any], shutdown_event: threading.Event) -> None:
    global file_handler
    db = None
    rabbitmq_client = None

    try:
        db = IngestorDB(db_params, file_handler)
        db.create_insights_table()
        logging.info("Conexão com o banco de dados estabelecida e tabela garantida.")

        rabbitmq_client = RabbitMQClient(
            config["RABBITMQ_USER"], config["RABBITMQ_PASSWORD"], config["RABBITMQ_HOST"], config["RABBITMQ_PORT"]
        )
        logging.info("Cliente RabbitMQ configurado.")

        # Consome mensagens enquanto não houver shutdown
        while not shutdown_event.is_set():
            rabbitmq_client.consume(config["RABBITMQ_QUEUE"], partial(on_rabbitmq_message, db=db, config=config))

    except KeyboardInterrupt:
        logging.info("Aplicação encerrada pelo usuário.")
    except Exception as e:
        logging.critical(f"Erro crítico inesperado na aplicação: {e}", exc_info=True)
    finally:
        if db:
            try:
                db.close()
                logging.info("Conexão com o banco de dados fechada.")
            except Exception as close_err:
                logging.error(f"Erro ao fechar conexão com o banco: {close_err}", exc_info=True)


# Função principal do serviço. Inicializa configs, banco, MQTT e inicia o loop.
def main() -> None:
    required_vars = [
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "MQTT_BROKER_HOST",
        "MQTT_BROKER_PORT",
        "MQTT_TOPIC",
        "RABBITMQ_HOST",
        "RABBITMQ_PORT",
        "RABBITMQ_QUEUE",
        "RABBITMQ_USER",
        "RABBITMQ_PASSWORD",
    ]

    try:
        config = get_env_vars(required_vars, logger=file_handler)

        db_params = {
            "dbname": config["POSTGRES_DB"],
            "user": config["POSTGRES_USER"],
            "password": config["POSTGRES_PASSWORD"],
            "host": config["POSTGRES_HOST"],
        }
    except ValueError as e:
        logging.critical(f"Erro crítico inesperado na aplicação: {e}", exc_info=True)
        sys.exit(1)

    # Evento para shutdown coordenado
    shutdown_event = threading.Event()

    mqtt_ingestor_thread = threading.Thread(target=mqtt_ingestor, args=(db_params, config, shutdown_event))
    rabbitmq_ingestor_thread = threading.Thread(target=rabbitmq_ingestor, args=(db_params, config, shutdown_event))

    mqtt_ingestor_thread.start()
    rabbitmq_ingestor_thread.start()

    try:
        while mqtt_ingestor_thread.is_alive() or rabbitmq_ingestor_thread.is_alive():
            # necessário para dectar o comando do terminal sem esperar as threads terminarem
            mqtt_ingestor_thread.join(timeout=1)
            rabbitmq_ingestor_thread.join(timeout=1)
    except KeyboardInterrupt:
        logging.info("Encerrando serviço...")
        shutdown_event.set()
        mqtt_ingestor_thread.join()
        rabbitmq_ingestor_thread.join()


if __name__ == "__main__":
    main()
