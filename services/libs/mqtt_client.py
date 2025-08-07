import paho.mqtt.client as mqtt
import logging
import threading
from typing import Callable, Optional, Any, Dict


# Esta classe encapsula toda a lógica de conexão, assinatura e recebimento de mensagens via MQTT.
class MQTTClient:
    # Inicializa o cliente MQTT, define callbacks e configura o logger.
    def __init__(
        self,
        broker_host: str,
        broker_port: int | str,
        topic: str | None = None,
        on_message: Optional[Callable[[Any, Any, Any], None]] = None,
        logger: Optional[logging.Handler] = None,
        client_id: str = "",
        userdata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.on_message = on_message
        self.userdata = userdata or {}

        self.logger = logging.getLogger("MQTTClient")
        if logger and logger not in self.logger.handlers:
            self.logger.addHandler(logger)
        self.logger.setLevel(logging.INFO)

        self.client = mqtt.Client(client_id=client_id, userdata=self.userdata)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.silent_reconnection = False

        if self.on_message is not None:
            self.client.on_message = self.on_message

    # Callback executado quando o cliente conecta ao broker MQTT.
    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
        if rc == 0:
            self.connection_log("Conectado ao Broker!")
            if self.topic:
                client.subscribe(self.topic)
        else:
            self.logger.error(f"Falha na conexão com Broker, código {rc}")

    # Evento de desconexão que loga a desconexão
    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        self.connection_log("Desconexão inesperada do Broker.")

    # Realiza a conexão ao broker MQTT e inicia o loop de escuta de mensagens.
    def connect_and_listen(self, timeout: Optional[int] = None) -> None:
        try:
            self.client.connect(self.broker_host, int(self.broker_port), 60)

            # timer necessário para shutdown
            if timeout is not None:
                self.silent_reconnection = True
                t = threading.Timer(timeout, self.disconnect)
                t.start()
                self.client.loop_forever()
                t.cancel()
            else:
                self.client.loop_forever()

        except Exception as e:
            self.logger.critical(f"Erro de conexão ou operação MQTT: {e}", exc_info=True)
            raise

    # Conecta ao broker MQTT sem bloquear a aplicação (para publicação)
    def connect(self) -> None:
        try:
            self.client.connect(self.broker_host, int(self.broker_port), 60)
            self.client.loop_start()
            self.connection_log("Conectado ao broker MQTT para publicação.")
        except Exception as e:
            self.logger.critical(f"Erro ao conectar ao broker MQTT: {e}", exc_info=True)
            raise

    # Publica uma mensagem JSON já formatada no tópico MQTT
    def publish(self, topic: str, payload: str) -> None:
        try:
            result = self.client.publish(topic, payload)
            result.wait_for_publish()
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                self.logger.error(f"Erro ao publicar no tópico {topic}: {result.rc}")
            else:
                self.connection_log(f"Payload publicado em {topic}")
        except Exception as e:
            self.logger.critical(f"Erro ao publicar MQTT: {e}", exc_info=True)
            raise

    # Encerra a conexão com o broker MQTT de forma segura.
    def disconnect(self) -> None:
        try:
            self.client.disconnect()
            self.connection_log("Desconectado do broker MQTT")
        except Exception as e:
            self.logger.error(f"Erro ao desconectar do broker MQTT: {e}", exc_info=True)

    # Utilitário para logging de conexão (evita logs repetitivos)
    def connection_log(self, msg: str) -> None:
        if self.silent_reconnection:
            return
        self.logger.info(msg)
