FROM python:3.6-slim
LABEL "project.home"="https://github.com/m3h7/coinlendingbot"

#
# Build: docker build -t <your_id>/coinlendingbot .
# Run: docker run -d -v /coinlendingbot_data:/data -p 8000:8000 <your_id>/coinlendingbot
#

WORKDIR /usr/src/app

COPY requirements.txt .
RUN apt-get update && apt-get -y upgrade && \
    apt-get -y install --no-install-recommends build-essential openssl && \
    pip install --no-cache-dir -r ./requirements.txt && \
    apt-get -y autoremove build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY . .

VOLUME /data

RUN ln -s /data/market_data market_data; \
    ln -s /data/logs logs; \
    ln -s /data/logs/botlog.json www/botlog.json;

EXPOSE 8000

CMD ["python", "lendingbot.py", "--config", "/data/conf/default.cfg", "--logconfig", "/data/conf/logging.ini"]
