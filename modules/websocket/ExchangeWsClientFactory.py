import logging
from autobahn.twisted.websocket import WebSocketClientFactory
from twisted.internet.protocol import ReconnectingClientFactory

from modules.websocket.WsConfig import WsConfig


class ExchangeWsClientFactory(ReconnectingClientFactory, WebSocketClientFactory):
    def __init__(self, exchange, data_processing):
        self.exchange = exchange

        WebSocketClientFactory.__init__(self, WsConfig[self.exchange]["ws_url"])

        self.logging = logging.getLogger(__name__)
        self.data_processing = data_processing
        self.proto = None
        self.lendingbook_list = []
        self.ticker_list = []

    def clientConnectionLost(self, connector, reason):
        self.logging.warn('Lost connection. Reason: {}'.format(reason))
        self.retry(connector)

    def clientConnectionFailed(self, connector, reason):
        self.logging.warn('Connection failed. Reason: {}'.format(reason))
        self.retry(connector)

    def websocket_opened(self, protocol):
        self.proto = protocol
        self.resetDelay()
        self._resubscribe_lendingbook()
        self._resubscribe_ticker()

    def websocket_closed(self):
        self.proto = None

    def startedConnecting(self, connector):
        self.logging.debug('startedConnecting')

    def subscribe_lendingbook(self, currency):
        if self.proto:
            self.proto.subscribe_lendingbook(currency)
            if currency not in self.lendingbook_list:
                self.lendingbook_list.append(currency)
        else:
            self.reactor.callLater(1, self.subscribe_lendingbook, currency)

    def unsubscribe_lendingbook(self, currency):
        if self.proto:
            self.proto.unsubscribe_lendingbook(currency)
            self.lendingbook_list.remove(currency)
        else:
            self.reactor.callLater(1, self.unsubscribe_lendingbook, currency)

    def _resubscribe_lendingbook(self):
        for currency in self.lendingbook_list:
            self.subscribe_lendingbook(currency)

    def subscribe_ticker(self, pair):
        if self.proto:
            self.proto.subscribe_ticker(pair)
            if pair not in self.ticker_list:
                self.ticker_list.append(pair)
        else:
            self.reactor.callLater(1, self.subscribe_ticker, pair)

    def unsubscribe_ticker(self, pair):
        if self.proto:
            self.proto.unsubscribe_ticker(pair)
            self.ticker_list.remove(pair)
        else:
            self.reactor.callLater(1, self.unsubscribe_ticker, pair)

    def _resubscribe_ticker(self):
        for pair in self.ticker_list:
            self.subscribe_ticker(pair)
