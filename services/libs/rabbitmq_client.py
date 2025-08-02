import pika
from pika.exceptions import AMQPConnectionError, ChannelError, AMQPError
import logging
from typing import Optional, Callable, Any, Union
from functools import partial
import json
import threading
import time


# Esta classe encapsula a lógica de conexão e publicação de mensagens no RabbitMQ.
class RabbitMQClient:
    # Inicializa o cliente RabbitMQ, define credenciais e configura o logger.
    def __init__(
        self,
        username: str,
        password: str,
        rabbitmq_host: str = "rabbitmq",
        rabbitmq_port: int | str = 5672,
        logger: Optional[logging.Handler] = None,
    ) -> None:
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.credentials = pika.PlainCredentials(username, password)
        self.connection = None

        self.logger = logging.getLogger("RabbitMQClient")
        if logger and logger not in self.logger.handlers:
            self.logger.addHandler(logger)
        self.logger.setLevel(logging.INFO)

    # Publica um alerta na fila especificada do RabbitMQ.
    # O alerta inclui tipo, severidade, mensagem, tópico de origem e valor.
    def publish(self, alert_type: str, severity: str, message: str, source_topic: str, value: int, queue: str) -> None:
        alert_payload = {
            "type": alert_type,
            "severity": severity,
            "message": message,
            "source_topic": source_topic,
            "value": value,
        }

        connection = None
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.rabbitmq_host, port=int(self.rabbitmq_port), credentials=self.credentials
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=queue, durable=True)
            channel.basic_publish(exchange="", routing_key=queue, body=json.dumps(alert_payload))
            self.logger.info(f"Alerta publicado na fila '{queue}' com sucesso: {alert_payload}")
        except AMQPConnectionError as conn_err:
            self.logger.error(f"Erro de conexão com RabbitMQ: {conn_err}", exc_info=True)
        except ChannelError as chan_err:
            self.logger.error(f"Erro no canal RabbitMQ: {chan_err}", exc_info=True)
        except AMQPError as amqp_err:
            self.logger.error(f"Erro AMQP no RabbitMQ: {amqp_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Erro inesperado ao publicar alerta no RabbitMQ: {e}", exc_info=True)
        finally:
            if connection and getattr(connection, "is_open", False):
                connection.close()

    # Escuta mensagens de uma fila e executa uma função callback para cada mensagem recebida. Faz 10 tentativas de conexão por padrão.
    # on_message_callback: função que recebe os parâmetros (channel, method, properties, body).
    def consume(
        self,
        queue: str,
        on_message_callback: Union[Callable[..., Any], partial],
        timeout: Optional[int] = None,
        retries: int = 10,
        delay: int = 5,
    ) -> None:
        attempt = 0
        while attempt < retries:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self.rabbitmq_host, port=int(self.rabbitmq_port), credentials=self.credentials
                    )
                )
                channel = self.connection.channel()
                channel.queue_declare(queue=queue, durable=True)
                self.logger.info(f"Escutando fila '{queue}'...")

                channel.basic_consume(queue=queue, on_message_callback=on_message_callback, auto_ack=True)

                # timer necessário para shutdown
                if timeout is not None:
                    t = threading.Timer(timeout, self.stop, args=(channel,))
                    t.start()
                    channel.start_consuming()
                    t.cancel()
                else:
                    channel.start_consuming()
                break 
            except AMQPConnectionError as conn_err:
                self.logger.error("Erro de conexão com RabbitMQ")
                attempt += 1
                if attempt < retries: # quantidade limitada de tentativas
                    self.logger.info(f"Tentando novamente em {delay} segundos... ({attempt}/{retries})")
                    time.sleep(delay)
                else:
                    self.logger.critical(f"Não foi possível conectar ao RabbitMQ após várias tentativas: {conn_err}", exc_info=True)
            except ChannelError as chan_err:
                self.logger.error(f"Erro no canal RabbitMQ: {chan_err}", exc_info=True)
                break # tentativas devem ser somente em erros de conexão, quebra loop em outros erros
            except AMQPError as amqp_err:
                self.logger.error(f"Erro AMQP no RabbitMQ: {amqp_err}", exc_info=True)
                break
            except Exception as e:
                self.logger.error(f"Erro inesperado ao consumir fila RabbitMQ: {e}", exc_info=True)
                break
            finally:
                self.close_connection()

    def stop(self, channel: Any) -> None:
        try:
            channel.stop_consuming()
            self.logger.info(f"Consumo da fila interrompido.")
        except Exception as e:
            self.logger.error(f"Erro ao interromper consumo: {e}", exc_info=True)

    # Fecha a escuta se estiver aberta
    def close_connection(self) -> None:
        if self.connection and getattr(self.connection, "is_open", False):
            self.connection.close()
            self.logger.info("Conexão RabbitMQ fechada.")
