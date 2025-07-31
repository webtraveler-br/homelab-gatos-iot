FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

# instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# CMD: exibe variáveis de ambiente relevantes e inicia o serviço
CMD ["sh", "-c", "echo \"DB_HOST=$DB_HOST\"; echo \"DB_PORT=$DB_PORT\"; echo \"DB_DATABASE=$DB_DATABASE\"; echo \"DB_USERNAME=$DB_USERNAME\"; echo \"DB_PASSWORD=$DB_PASSWORD\"; python app.py"]