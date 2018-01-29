from autobahn.twisted.websocket import WebSocketClientProtocol
import logging
import json


class BitfinexWsClientProtocol(WebSocketClientProtocol):
    RESPONSE_CODE = {
        # Generic Error Codes
        "10000": "Unknown event",
        "10001": "Unknown pair",
        "10011": "Unknown Book precision",
        "10012": "Unknown Book length",
        # Error Codes Subscibe
        "10300": "Subscription failed",
        "10301": "Already subscribed",
        "10302": "Unknown channel",
        # Error Codes Unsubscribe
        "10400": "Subscription failed",
        "10401": "Not subscribed",
        # Info Codes
        "20051": "Stop/Restart Websocket Server",
        "20060": "Entering in Maintenance mode",
        "20061": "Maintenance ended"
        }

    def __init__(self):
        super(BitfinexWsClientProtocol, self).__init__()
        self.logging = logging.getLogger(__name__)
        self.channels = {}

    def onConnect(self, request):
        pass

    def onOpen(self):
        self.logging.info("WS opened")
        self.channels = {}
        self.factory.websocket_opened(self)
        self.ping()

    def onClose(self, wasClean, code, reason):
        self.logging.info("WS closed: code {0}, reason: {1}".format(code, reason))
        self.factory.websocket_closed()

    def onMessage(self, payload, isBinary):
        msg = json.loads(payload.decode('utf8'))
        if isinstance(msg, dict):
            self._received_event(msg)
        elif isinstance(msg, list):
            self._received_data(msg)

    def ping(self):
        self._send({'event': 'ping'})
        self.factory.reactor.callLater(5, self.ping)

    def _received_event(self, msg):
        self.logging.debug("event: {}".format(msg))
        event = msg["event"]
        if event in ["info", "pong"]:
            pass
        elif event == "subscribed":
            # New subscribed channels
            self.channels[msg["chanId"]] = msg
        elif event == "unsubscribed":
            if msg["status"] == "OK":
                channel = self.channels[msg["chanId"]]["channel"]
                if channel == "book":
                    self.factory.data_processing('lendingbook', 'remove',
                                                 {"symbol": self.channels[msg["chanId"]]["currency"]})
                elif channel == "ticker":
                    self.factory.data_processing('ticker', 'remove',
                                                 {"pair": self.channels[msg["chanId"]]["pair"]})
                del self.channels[msg["chanId"]]
            else:
                self.logging.error("Unsubscribe response: {}".format(msg))
        elif event == "error":
            code = str(msg["code"])
            self.logging.error("{} {}".format(BitfinexWsClientProtocol.RESPONSE_CODE[code], msg))
        else:
            self.logging.error("event unknown: {}".format(msg))

    def _received_data(self, msg):
        chanId = msg[0]
        if chanId not in self.channels:
            self.logging.error("Channel unknown: {} : {}".format(chanId, msg))
            return
        data = msg[1]
        if isinstance(data, str):
            if data == "hb":
                self._heart_beat(chanId)
        else:
            channel = self.channels[chanId]["channel"]
            if channel == "book":
                self._update_book(self.channels[chanId]["symbol"], data)
            elif channel == "ticker":
                self._update_ticker(self.channels[chanId]["pair"], data)

    def _heart_beat(self, chanId):
        channel = self.channels[chanId]["channel"]
        if channel == "book":
            self.factory.data_processing("lendningbook", "heart_beat", {
                "symbol": self.channels[chanId]["symbol"]
            })
        elif channel == "ticker":
            self.factory.data_processing("ticker", "heart_beat", {
                "pair": self.channels[chanId]["pair"]
            })

    def _update_book(self, symbol, data):
        values = data if isinstance(data[0], list) else [data]
        for val in values:
            rate, period, count, amount = val
            book_entry = "{:.12f}_{:02d}".format(rate, period)
            side = "bids" if (amount < 0) else "asks"
            if count:
                # add / update
                self.factory.data_processing('lendingbook', 'update', {
                    "symbol": symbol[1:],
                    "entry": book_entry,
                    "side": side,
                    "value": {"rate": rate, "amount": abs(amount), "period": period}
                })
            else:
                # Delete
                self.factory.data_processing('lendingbook', 'delete', {
                    "symbol": symbol[1:],
                    "entry": book_entry,
                    "side": side
                })

    def _update_ticker(self, pair, data):
        self.factory.data_processing('ticker', 'update', {
            "pair": pair,
            "bid": data[0],
            "bid_size": data[1],
            "ask": data[2],
            "ask_size": data[3],
            "daily_change": data[4],
            "daily_change_percentage": data[5],
            "last_price": data[6],
            "volume": data[7],
            "high": data[8],
            "low": data[9]
        })

    def _send(self, data):
        self.logging.debug("{}".format(data))
        self.sendMessage(json.dumps(data).encode('utf8'))

    def _find_channel_id(self, symbol):
        symbol_type = 'currency' if len(symbol) == 3 else 'pair'
        for key in self.channels:
            if symbol_type in self.channels[key] and self.channels[key][symbol_type] == symbol:
                return key
        return 0

    def subscribe_lendingbook(self, currency):
        self.unsubscribe_lendingbook(currency)
        self._send({
            "event": "subscribe",
            "channel": "book",
            "symbol": "f{}".format(currency),
            "prec": "P0",
            "freq": "F0",
            "length": "100"
        })

    def unsubscribe_lendingbook(self, currency):
        channelId = self._find_channel_id(currency)
        if channelId:
            self._send({
                "event": "unsubscribe",
                "chanId": channelId
            })

    def subscribe_ticker(self, pair):
        self._send({
            "event": "subscribe",
            "channel": "ticker",
            "symbol": "t{}".format(pair.upper()),
        })

    def unsubscribe_ticker(self, pair):
        channelId = self._find_channel_id(pair)
        if channelId:
            self._send({
                "event": "unsubscribe",
                "chanId": channelId
            })
