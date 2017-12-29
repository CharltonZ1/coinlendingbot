import logging
import threading
import time
from datetime import datetime
from twisted.internet import reactor
from twisted.internet import ssl

from coinlendingbot.websocket.WsConfig import WsConfig
from coinlendingbot.websocket import ExchangeWsClientFactory


class ExchangeWsClient(threading.Thread):
    def __init__(self, exchange):
        self.exchange = exchange

        super(ExchangeWsClient, self).__init__(name=self.__str__())

        self.logging = logging.getLogger(__name__)
        self.daemon = True
        self.lendingbook = {}
        self.ticker = {}

        self.factory = ExchangeWsClientFactory(self.exchange, self._data_processing)

    def __str__(self):
        return "{}_{}".format(__name__, self.exchange)

    def __repr__(self):
        return self.__str__()

    def run(self):
        self.factory.protocol = WsConfig[self.exchange]["protocol"]
        reactor.connectSSL(WsConfig[self.exchange]["ws_host"], WsConfig[self.exchange]["ws_port"],
                           self.factory, ssl.ClientContextFactory())
        reactor.run(installSignalHandlers=0)

    def subscribe_lendingbook(self, currency):
        self.logging.debug(currency)
        self.factory.subscribe_lendingbook(currency)

    def unsubscribe_lendingbook(self, currency):
        self.factory.unsubscribe_lendingbook(currency)

    def return_lendingbook_list(self):
        return self.lendingbook.keys()

    def return_lendingbook(self, currency, limit=0):
        limit = 100 if limit == 0 or limit > 100 else limit
        book = {"asks": [], "bids": []}
        if currency not in self.lendingbook:
            self.logging.debug("Currency {} not subribed: subscribing...".format(currency))
            self.subscribe_lendingbook(currency)
            while currency not in self.lendingbook:
                time.sleep(1)
        for site in book:
            count = 0
            for p in sorted(self.lendingbook[currency][site].keys(), reverse=True if site == "bids" else False):
                book[site].append(self.lendingbook[currency][site][p])
                count += 1
                if count == limit:
                    break
        book["update_time"] = self.lendingbook[currency]["update_time"]
        return book

    def subscribe_ticker(self, pair):
        self.factory.subscribe_ticker(pair)

    def unsubscribe_ticker(self, pair):
        self.factory.unsubscribe_ticker(pair)

    def return_ticker(self):
        return self.ticker

    def _data_processing(self, datatype, action, data):
        symbol = data["symbol"] if "symbol" in data else data["pair"]
        self.logging.debug("{}, {}, {}".format(datatype, action, symbol))
        now = datetime.utcnow()
        try:
            if datatype == "lendingbook":
                if action == "update":
                    if symbol not in self.lendingbook:
                        self.lendingbook[symbol] = {}
                        self.lendingbook[symbol]["asks"] = {}
                        self.lendingbook[symbol]["bids"] = {}
                    self.lendingbook[symbol][data["side"]][data["entry"]] = data["value"]
                    self.lendingbook[symbol]["update_time"] = now
                elif action == "delete":
                    if data["entry"] in self.lendingbook[symbol][data["side"]]:
                        del self.lendingbook[symbol][data["side"]][data["entry"]]
                    self.lendingbook[symbol]["update_time"] = now
                elif action == "remove":
                    if symbol in self.lendingbook:
                        del self.lendingbook[symbol]
                elif action == "heart_beat":
                    self.lendingbook[symbol]["update_time"] = now
            elif datatype == "ticker":
                if action == "update":
                    self.ticker[symbol] = data
                    self.ticker[symbol]["update_time"] = now
                elif action == "remove":
                    if symbol in self.ticker:
                        del self.ticker[symbol]
                elif action == "heart_beat":
                    self.ticker[symbol]["update_time"] = now
        except Exception as ex:
            self.logging.error("{}: datatype={}, action={}, data={}".format(ex, datatype, action, data))
