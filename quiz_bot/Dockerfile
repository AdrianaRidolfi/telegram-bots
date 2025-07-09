FROM python:3.11-slim

WORKDIR /app

# Copia requirements e installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del bot
COPY . .

# Espone la porta per FastAPI
EXPOSE 8000

CMD ["python", "bot.py"]
