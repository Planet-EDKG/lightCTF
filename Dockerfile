# Basis-Image mit Python
FROM python:3.11

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere die Anwendungsdateien ins Container-Image
COPY . /app

# Installiere Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Erstelle den Ordner für Datei-Uploads
RUN mkdir -p uploads

# Setze Umgebungsvariablen
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=production

# Öffne Port 5000 für Flask
EXPOSE 5000

# Starte die Anwendung
CMD ["flask", "run"]
