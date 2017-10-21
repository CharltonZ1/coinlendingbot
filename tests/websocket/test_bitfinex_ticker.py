import pytest
import logging

import os
import sys
import inspect
import time
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
sys.path.insert(0, parentdir)


from modules.websocket import ExchangeWsClient  # nopep8

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')


@pytest.fixture
def websocket():
    ws = ExchangeWsClient('BITFINEX')
    ws.start()
    return ws


def test_ticker_subscribe(websocket):
    websocket.subscribe_ticker('BTCUSD')
    time.sleep(3)
    ticker = websocket.return_ticker()
    assert 'BTCUSD' == ticker['BTCUSD']['pair']
    websocket.unsubscribe_ticker('BTCUSD')
    time.sleep(2)
    ticker = websocket.return_ticker()
    assert {} == ticker
