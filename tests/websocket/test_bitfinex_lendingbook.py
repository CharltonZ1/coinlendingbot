import pytest
import logging

import os
import sys
import inspect
import time
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
sys.path.insert(0, parentdir)


from coinlendingbot.websocket import ExchangeWsClient  # nopep8

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')


@pytest.fixture
def websocket():
    ws = ExchangeWsClient('BITFINEX')
    ws.start()
    return ws


def test_lendingbook_autosubscribe(websocket):
    book = websocket.return_lendingbook('USD')
    print(book)
    assert book['update_time']
    assert book['bids']
    assert book['asks']
    websocket.unsubscribe_lendingbook('USD')
    time.sleep(2)
    book_list = websocket.return_lendingbook_list()
    assert [] == book_list
