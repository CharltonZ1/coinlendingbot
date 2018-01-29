import time
import threading

# Hack to get relative imports - probably need to fix the dir structure instead but we need this at the minute for
# pytest to work
import os
import sys
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from coinlendingbot.Bitfinex import Bitfinex  # nopep8
import coinlendingbot.Configuration as Config  # nopep8
import coinlendingbot.Data as Data  # nopep8

Config.init(open('bitfinex_test.cfg'), Data)
api = Bitfinex(Config, None)
start_time = time.time()


def multiple_api_queries(n):
    try:
        for i in range(n):
            print("Thread {}".format(i + 1))
            thread1 = threading.Thread(target=call_get_open_loan_offers, args=[(i+1)])
            thread1.start()
    except Exception as e:
        assert False, 'Thread ' + str(i + 1) + ':' + e.message


# Test fast api calls
def test_multiple_calls():
    multiple_api_queries(270)


def call_get_open_loan_offers(i):
    api.return_open_loan_offers()
    print("API Call {} sec: {} - {}".format(i, time.time(), start_time))
