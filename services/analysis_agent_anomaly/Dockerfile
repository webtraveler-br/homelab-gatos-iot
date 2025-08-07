FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

# Instala as dependências do serviço
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# CMD: inicia o serviço de análise
CMD ["python", "app.py"]
