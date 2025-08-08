import psycopg
import time
import logging
from typing import Optional
from threading import local


# Classe para gerenciar a conexão e operações com o banco de dados PostgreSQL para logs de sensores e insights.
class IngestorDB:
    missing_conn = "Conexão com o banco não está estabelecida."

    # Inicializa a classe, configura o logger e conecta ao banco.
    # db_params: configurações do banco (host, dbname, user, password, etc).
    def __init__(self, db_params: dict, log_handler: Optional[logging.Handler] = None) -> None:
        self.db_params = db_params
        self._local = local()  # armazenamento seguro para threads

        self.logger = logging.getLogger("SensorLogsDB")
        if log_handler and log_handler not in self.logger.handlers:
            self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)
        self.connect()

    # Tenta conectar ao banco de dados.
    # Faz até 'retries' tentativas, esperando 'delay' segundos entre elas.
    def connect(self, retries: int = 5, delay: int = 5) -> None:
        for i in range(retries):
            try:
                self._local.conn = psycopg.connect(**self.db_params)
                self.logger.info("Conexão com o PostgreSQL estabelecida com sucesso.")
                return
            except (psycopg.OperationalError, psycopg.DatabaseError) as e:
                self.logger.error(f"Erro ao conectar ao PostgreSQL: {e}")
                if i < retries - 1:
                    self.logger.info(f"Tentando novamente em {delay} segundos... ({i+1}/{retries})")
                    time.sleep(delay)
                else:
                    self.logger.critical("Não foi possível conectar ao banco de dados após várias tentativas.")
                    raise Exception(self.missing_conn)

    # Retorna a conexão ativa com o banco.
    # Se estiver fechada ou nula, tenta reconectar automaticamente.
    @property
    def connection(self) -> psycopg.Connection:
        # a thread pode não ter o conn
        conn = getattr(self._local, "conn", None)
        if conn is None or conn.closed:
            self.connect()
            conn = self._local.conn
        return conn

    # Função interna para criar tabelas e índices no banco.
    def _create_table(self, ddl: str, log_msg: str) -> None:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(ddl)
                self.connection.commit()
                self.logger.info(log_msg)
        except (psycopg.OperationalError, psycopg.DatabaseError) as db_err:
            self.logger.error(f"Erro de banco de dados ao criar tabela: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Erro inesperado ao criar tabela: {e}", exc_info=True)

    # Garante que a tabela sensor_logs existe no banco, criando-a se necessário.
    def create_sensor_logs_table(self) -> None:
        ddl = """
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                topic VARCHAR(255) NOT NULL,
                payload JSONB NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sensor_logs_timestamp ON sensor_logs (timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_sensor_logs_payload ON sensor_logs USING GIN (payload);
        """
        self._create_table(ddl, "Tabela sensor_logs garantida no banco de dados.")

    # Garante que a tabela insights existe no banco, criando-a se necessário.
    def create_insights_table(self) -> None:
        ddl = """
            CREATE TABLE IF NOT EXISTS insights (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                type VARCHAR(100) NOT NULL,
                severity VARCHAR(50),
                payload JSONB NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_insights_timestamp ON insights (timestamp DESC);
        """
        self._create_table(ddl, "Tabela insights garantida no banco de dados.")

    # Função interna que faz um INSERT genérico.
    def _insert(self, query: str, params: tuple, log_msg: str) -> None:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                self.logger.info(log_msg)
        except (psycopg.OperationalError, psycopg.DatabaseError, TypeError) as db_err:
            self.logger.error(f"Erro de banco de dados ao inserir: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Erro inesperado ao inserir: {e}", exc_info=True)

    # Insere um novo registro de sensor na tabela sensor_logs.
    def insert_log(self, topic: str, message: str) -> None:
        self._insert(
            "INSERT INTO sensor_logs (topic, payload) VALUES (%s, %s)",
            (topic, message),
            f"Log inserido: tópico={topic}",
        )

    # Insere um novo insight (alerta/evento) na tabela insights.
    def insert_insight(self, type: str, severity: str, payload: str) -> None:
        self._insert(
            "INSERT INTO insights (type, severity, payload) VALUES (%s, %s, %s)",
            (type, severity, payload),
            f"Insight inserido: type={type}, severity={severity}",
        )

    # Fecha a conexão com o banco de dados.
    def close(self) -> None:
        try:
            conn = getattr(self._local, "conn", None)
            if conn:
                conn.close()
                self._local.conn = None
                self.logger.info("Conexão com o banco de dados fechada.")
        except (psycopg.OperationalError, psycopg.DatabaseError) as db_err:
            self.logger.error(f"Erro de banco de dados ao fechar conexão: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Erro inesperado ao fechar conexão: {e}", exc_info=True)
