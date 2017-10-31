FROM python:2.7-slim
LABEL "project.home"="https://github.com/BitBotFactory/poloniexlendingbot"

#
# Build: docker build -t <your_id>/pololendingbot .
# Run: docker run -d -v /pololendingbot_data:/data -p 8000:8000 <your_id>/pololendingbot
#

WORKDIR /usr/src/app

COPY requirements.txt .
RUN apt-get update && apt-get -y upgrade && \
    apt-get -y install build-essential openssl && \
    pip install --no-cache-dir -r ./requirements.txt && \
    apt-get -y autoremove build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY . .

VOLUME /data

RUN ln -s /data/market_data market_data; \
    ln -s /data/logs logs; \
    ln -s /data/logs/botlog.json www/botlog.json;

EXPOSE 8000

CMD ["python", "lendingbot.py", "-cfg", "/data/conf/default.cfg", "-logcfg", "/data/conf/logging.ini"]
