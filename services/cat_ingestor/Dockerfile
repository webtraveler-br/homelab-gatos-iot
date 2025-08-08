FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

# instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# CMD: inicia o serviço
CMD ["python", "app.py"]