# Dockerfile
FROM pypy:3.10-slim-bullseye

WORKDIR /app

# install build tools needed for pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# install python packages
COPY requirements.txt .
RUN pypy3 -m pip install --no-cache-dir -r requirements.txt

# copy all application code
COPY ./app /app

# set up user and permissions
RUN useradd --create-home appuser
RUN chown -R appuser:appuser /app
USER appuser

# expose port and run the application
EXPOSE 5000
CMD ["pypy3", "main.py"]
