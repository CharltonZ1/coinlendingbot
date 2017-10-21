from modules.websocket import BitfinexWsClientProtocol

WsConfig = {
    "BITFINEX": {
        "ws_host": "api.bitfinex.com",
        "ws_port": 443,
        "ws_url": "wss://api.bitfinex.com/ws/2",
        "protocol": BitfinexWsClientProtocol
    }
}
