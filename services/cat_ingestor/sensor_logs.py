import psycopg
import time
import logging
import os

class SensorLogsDB:
    missing_conn = "Conexão com o banco não está estabelecida."

    def __init__(self, db_params, log_handler=None):
        self.db_params = db_params
        self.conn = None
        # cria um logger SensorLogsDB e adiciona ele como handler
        self.logger = logging.getLogger("SensorLogsDB")
        if log_handler and log_handler not in self.logger.handlers:
            self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)
        self.connect()
    
    def connect(self, retries=5, delay=5):
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
        if self.conn == None or self.conn.closed:
            self.connect()
        return self.conn
    
    def create_table(self):
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
    
    def insert_log(self, topic, message):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO sensor_logs (topic, payload) VALUES (%s, %s)", (topic, message))
                self.conn.commit()
                self.logger.info(f"Log inserido: tópico={topic}")
        except Exception as e:
            self.logger.error(f"Erro ao inserir log: {e}")
    
    def close(self):
        try:
            self.connection.close()
            self.conn = None
            self.logger.info("Conexão com o banco de dados fechada.")
        except Exception as e:
            self.logger.error(f"Erro ao fechar conexão: {e}")