import psycopg
import time
import logging
import os

class SensorLogsDB:
    """
    Classe para gerenciar a conexão e operações com o banco de dados PostgreSQL para logs de sensores.
    """
    missing_conn = "Conexão com o banco não está estabelecida."

    def __init__(self, db_params: dict, log_handler: logging.Handler = None) -> None:
        """
        Inicializa a classe, configura logger e conecta ao banco.
        db_params: dict com configs do banco.
        log_handler: handler opcional para logs em arquivo.
        """
        self.db_params = db_params
        self.conn = None
        # cria um logger SensorLogsDB e adiciona ele como handler
        self.logger = logging.getLogger("SensorLogsDB")
        if log_handler and log_handler not in self.logger.handlers:
            self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)
        self.connect()
    
    def connect(self, retries: int = 5, delay: int = 5) -> None:
        """
        Tenta conectar ao banco de dados, com retries e delay. Lança exceção se não conseguir.
        """
        for i in range(retries):
            try:
                self.conn = psycopg.connect(**self.db_params)
                self.logger.info("Conexão com o PostgreSQL estabelecida com sucesso.")
                return
            except psycopg.OperationalError as e:
                self.logger.error(f"Erro ao conectar ao PostgreSQL: {e}")
                if i < retries - 1:
                    self.logger.info(f"Tentando novamente em {delay} segundos... ({i+1}/{retries})")
                    time.sleep(delay)
                else:
                    self.logger.critical("Não foi possível conectar ao banco de dados após várias tentativas.")
                    raise Exception(self.missing_conn)

    @property
    def connection(self):
        """
        Retorna a conexão ativa com o banco, reconectando se necessário.
        """
        if self.conn == None or self.conn.closed:
            self.connect()
        return self.conn
    
    def create_table(self) -> None:
        """
        Cria a tabela sensor_logs e índices se não existirem.
        """
        with self.connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensor_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    topic VARCHAR(255) NOT NULL,
                    payload JSONB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sensor_logs_timestamp ON sensor_logs (timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_sensor_logs_payload ON sensor_logs USING GIN (payload);
            """)
            self.conn.commit()
            self.logger.info("Tabela sensor_logs garantida no banco de dados.")
    
    def insert_log(self, topic: str, message: str) -> None:
        """
        Insere um novo log na tabela sensor_logs.
        topic: nome do tópico MQTT.
        message: payload da mensagem (JSON como string).
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO sensor_logs (topic, payload) VALUES (%s, %s)", (topic, message))
                self.conn.commit()
                self.logger.info(f"Log inserido: tópico={topic}")
        except psycopg.OperationalError as db_conn_err:
            self.logger.error(f"Erro de conexão com o banco de dados ao inserir log: {db_conn_err}", exc_info=True)
        except psycopg.DatabaseError as db_err:
            self.logger.error(f"Erro de banco de dados ao inserir log: {db_err}", exc_info=True)
        except TypeError as type_err:
            self.logger.error(f"Tipo de dado inválido ao inserir log: {type_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Erro inesperado ao inserir log: {e}", exc_info=True)
    
    def close(self) -> None:
        """
        Fecha a conexão com o banco de dados.
        """
        try:
            self.connection.close()
            self.conn = None
            self.logger.info("Conexão com o banco de dados fechada.")
        except psycopg.OperationalError as db_conn_err:
            self.logger.error(f"Erro de conexão ao fechar banco de dados: {db_conn_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Erro inesperado ao fechar conexão: {e}", exc_info=True)