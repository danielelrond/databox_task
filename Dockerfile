
FROM python:3.8-slim


WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


RUN apt-get update && apt-get install -y git && \
    git clone https://github.com/databox/databox-python.git /databox-python && \
    pip install /databox-python/src && \
    rm -rf /databox-python

COPY . .


EXPOSE 5022

CMD ["python", "app.py"]
