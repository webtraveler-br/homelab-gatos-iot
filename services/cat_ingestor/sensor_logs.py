import psycopg
import time

class SensorLogsDB:
    missing_conn = "Conexão com o banco não está estabelecida."

    def __init__(self, db_params):
        self.db_params = db_params
        self.conn = None
        self.connect()
    
    def connect(self, retries=5, delay=5):
        for i in range(retries):
            try:
                self.conn = psycopg.connect(**self.db_params)
                print("Conexão com o PostgreSQL estabelecida com sucesso.")
                return
            except psycopg.OperationalError as e:
                print(f"Erro ao conectar ao PostgreSQL: {e}")
                if i < retries - 1:
                    print(f"Tentando novamente em {delay} segundos... ({i+1}/{retries})")
                    time.sleep(delay)
                else:
                    print("Não foi possível conectar ao banco de dados após várias tentativas.")
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
    
    def insert_log(self, topic, message):
        with self.connection.cursor() as cursor:
            cursor.execute("INSERT INTO sensor_logs (topic, payload) VALUES (%s, %s)", (topic, message))
            self.conn.commit()
    
    def close(self):
        self.connection.close()
        self.conn = None