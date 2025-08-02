FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

# Instala as dependências do serviço
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# CMD: exibe variáveis de ambiente relevantes e inicia o serviço de análise
CMD ["sh", "-c", "echo 'MQTT_HOST=$MQTT_BROKER_HOST'; echo 'MQTT_PORT=$MQTT_BROKER_PORT'; echo 'MQTT_TOPIC=$MQTT_TOPIC'; echo 'RABBITMQ_HOST=$RABBITMQ_HOST'; echo 'RABBITMQ_PORT=$RABBITMQ_PORT'; python app.py"]
