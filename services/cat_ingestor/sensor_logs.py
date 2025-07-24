import psycopg
from dotenv import load_dotenv
import os

class SensorLogsDB:
    missing_conn = "Conexão com o banco não está estabelecida."

    def __init__(self, env_path='../../../../.env'):
        load_dotenv(env_path)
        self.conn = self.connect()
    
    def connect(self):
        return psycopg.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST", "localhost")
        )
    
    def create_table(self):
        if not self.conn:
            raise Exception(self.missing_conn)
        
        with self.conn.cursor() as cursor:
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
        if not self.conn:
            raise Exception(self.missing_conn)
        
        with self.conn.cursor() as cursor:
            cursor.execute("INSERT INTO sensor_logs (topic, payload) VALUES (%s, %s)", (topic, message))
            self.conn.commit()
    
    def close(self):
        if not self.conn:
            raise Exception(self.missing_conn)
        
        self.conn.close()
        self.conn = None