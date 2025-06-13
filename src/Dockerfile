FROM python:3.12.4-slim

RUN apt-get update && \
    apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/Asia/Vladivostok /etc/localtime && \
    echo "Asia/Vladivostok" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONDONTWRITEBYTECODE 1

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]