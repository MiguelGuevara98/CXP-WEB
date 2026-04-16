# Usar Python oficial ligero
FROM python:3.10-slim

# Directorio de trabajo en la raíz
WORKDIR /app

# Instalar dependencias
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el proyecto
COPY . .

# Usar el archivo lanzador run.py
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 run:app