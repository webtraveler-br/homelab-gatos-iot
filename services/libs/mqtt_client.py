import paho.mqtt.client as mqtt
import logging
from typing import Callable, Optional, Any, Dict
import threading


# Esta classe encapsula toda a lógica de conexão, assinatura e recebimento de mensagens via MQTT.
class MQTTClient:
    # Inicializa o cliente MQTT, define callbacks e configura o logger.
    def __init__(
        self,
        broker_host: str,
        broker_port: int | str,
        topic: str,
        on_message: Callable[[Any, Any, Any], None],
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
        self.client.on_message = self.on_message

    # Callback executado quando o cliente conecta ao broker MQTT.
    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
        if rc == 0:
            self.logger.info("Conectado ao Broker!")
            client.subscribe(self.topic)
        else:
            self.logger.error(f"Falha na conexão com Broker, código {rc}")

    # Realiza a conexão ao broker MQTT e inicia o loop de escuta de mensagens.
    # Em caso de erro, registra no log e relança a exceção para tratamento externo.
    def connect_and_loop(self, timeout: Optional[int] = None) -> None:
        try:
            self.client.connect(self.broker_host, int(self.broker_port), 60)

            # timer necessário para shutdown
            if timeout is not None:
                t = threading.Timer(timeout, self.disconnect)
                t.start()
                self.client.loop_forever()
                t.cancel()
            else:
                self.client.loop_forever()

        except Exception as e:
            self.logger.critical(f"Erro de conexão ou operação MQTT: {e}", exc_info=True)
            raise

    # Encerra a conexão com o broker MQTT de forma segura.
    # Registra qualquer erro ocorrido durante o processo de desconexão.
    def disconnect(self) -> None:
        try:
            self.client.disconnect()
            self.logger.info("Desconectado do broker MQTT")
        except Exception as e:
            self.logger.error(f"Erro ao desconectar do broker MQTT: {e}", exc_info=True)
