import paho.mqtt.client as mqtt
import sys
import json
import os
import logging
from sensor_logs import SensorLogsDB

# configura logging para console e arquivo (logs/cat_ingestor.log)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'cat_ingestor.log')

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

# valida e retorna as variaveis de ambiente
def get_env_vars() -> dict:
    """
    Lê e valida as variáveis de ambiente necessárias para o funcionamento do serviço.
    Retorna um dicionário com as configurações. Encerra o programa se faltar alguma variável.
    """
    required_vars = [
        "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST",
        "MQTT_BROKER_HOST", "MQTT_BROKER_PORT", "MQTT_TOPIC"
    ]
    config = {var: os.getenv(var) for var in required_vars}
    missing_vars = [var for var, val in config.items() if val == None]
    if missing_vars:
        logging.error(f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing_vars)}")
        sys.exit(1)
    
    config["MQTT_BROKER_PORT"] = int(config["MQTT_BROKER_PORT"])
    return config

# conexão com o MQTT
def on_connect(client: mqtt.Client, userdata: dict, flags: dict, rc: int) -> None:
    """
    Handler chamado ao conectar no broker MQTT. Faz subscribe no tópico configurado.
    """
    if rc == 0:
        logging.info("Conectado ao Broker!")
        client.subscribe(userdata["config"]["MQTT_TOPIC"])
    else:
        logging.error(f"Falha na conexão com Broker, código {rc}")

# inserção da mensagem no db
def on_message(client: mqtt.Client, userdata: dict, message: mqtt.MQTTMessage) -> None:
    """
    Handler chamado ao receber mensagem MQTT. Decodifica, valida e insere no banco.
    """
    db = userdata['db']
    topic = message.topic
    mqtt_message_str = message.payload.decode('utf-8')
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

def main() -> None:
    """
    Função principal do serviço. Inicializa configs, banco, MQTT e inicia o loop.
    """
    config = get_env_vars()

    db_params = {
        'dbname': config["POSTGRES_DB"],
        'user': config["POSTGRES_USER"],
        'password': config["POSTGRES_PASSWORD"],
        'host': config["POSTGRES_HOST"]
    }

    db = None

    try:
        db = SensorLogsDB(db_params, file_handler)
        db.create_table()
        logging.info("Conexão com o banco de dados estabelecida e tabela garantida.")

        client_userdata = {'db': db, 'config': config} # dados necessários para as handlers de evento
        client = mqtt.Client(client_id="cat_ingestor_app", userdata=client_userdata)
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(config["MQTT_BROKER_HOST"], config["MQTT_BROKER_PORT"], 60)
        client.loop_forever()

    except KeyboardInterrupt:
        logging.info("Aplicação encerrada pelo usuário.")
    except mqtt.MQTTException as mqtt_err:
        logging.critical(f"Erro de conexão ou operação MQTT: {mqtt_err}", exc_info=True)
    except Exception as e:
        logging.critical(f"Erro crítico inesperado na aplicação: {e}", exc_info=True)
    finally:
        # melhor forma para garantir o encerramento do banco de dados
        if db:
            try:
                db.close()
                logging.info("Conexão com o banco de dados fechada.")
            except Exception as close_err:
                logging.error(f"Erro ao fechar conexão com o banco: {close_err}", exc_info=True)
        sys.exit(0)

if __name__ == "__main__":
    main()