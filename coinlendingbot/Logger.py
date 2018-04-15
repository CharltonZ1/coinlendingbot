# coding=utf-8
import datetime
import io
import json
import time

import coinlendingbot.Configuration as Config
from coinlendingbot.RingBuffer import RingBuffer
from coinlendingbot.Notify import send_notification


class JsonOutput(object):
    def __init__(self, file, logLimit, exchange=''):
        self.jsonOutputFile = file
        self.jsonOutput = {}
        self.clearStatusValues()
        self.jsonOutputLog = RingBuffer(logLimit)
        self.jsonOutput['exchange'] = exchange
        self.jsonOutput['label'] = Config.get("BOT", "label", "Lending Bot")

    def status(self, status, time, days_remaining_msg):
        self.jsonOutput["last_update"] = time + days_remaining_msg
        self.jsonOutput["last_status"] = status

    def printline(self, line):
        line = line.replace("\n", ' | ')
        self.jsonOutputLog.append(line)

    def writeJsonFile(self):
        with io.open(self.jsonOutputFile, 'w', encoding='utf-8') as f:
            self.jsonOutput["log"] = self.jsonOutputLog.get()
            f.write(json.dumps(self.jsonOutput, ensure_ascii=True, sort_keys=True))
            f.close()

    def addSectionLog(self, section, key, value):
        if section not in self.jsonOutput:
            self.jsonOutput[section] = {}
        if key not in self.jsonOutput[section]:
            self.jsonOutput[section][key] = {}
        self.jsonOutput[section][key] = value

    def statusValue(self, coin, key, value):
        if coin not in self.jsonOutputCoins:
            self.jsonOutputCoins[coin] = {}
        self.jsonOutputCoins[coin][key] = str(value)

    def clearStatusValues(self):
        self.jsonOutputCoins = {}
        self.jsonOutput["raw_data"] = self.jsonOutputCoins
        self.jsonOutputCurrency = {}
        self.jsonOutput["outputCurrency"] = self.jsonOutputCurrency

    def outputCurrency(self, key, value):
        self.jsonOutputCurrency[key] = str(value)


class Logger(object):
    def __init__(self, json_file, json_log_size, exchange):
        self._lent = ''
        self._daysRemaining = ''
        self.output = JsonOutput(json_file, json_log_size, exchange)
        self.compactLog = bool(Config.get('BOT', 'jsonlogcompact', False))
        self.refreshStatus()
        self.persistStatus()

    @staticmethod
    def timestamp():
        ts = time.time()
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    def log(self, msg):
        log_message = "{0} {1}".format(self.timestamp(), msg)
        self.output.printline(log_message)
        self.refreshStatus()

    def log_error(self, msg):
        log_message = "{0} Error {1}".format(self.timestamp(), msg)
        self.output.printline(log_message)
        self.refreshStatus()

    def offer(self, amt, cur, rate, days, msg):
        line = self.timestamp() + ' Placing ' + str(amt) + ' ' + str(cur) + ' at ' + str(
            float(rate) * 100) + '% for ' + days + ' days... ' + self.digestApiMsg(msg)
        self.output.printline(line)
        if self.compactLog:
            self.output.statusValue(cur, 'log', '')
        self.refreshStatus()

    def cancelOrder(self, cur, msg):
        line = self.timestamp() + ' Canceling ' + str(cur) + ' order... ' + self.digestApiMsg(msg)
        self.output.printline(line)
        self.refreshStatus()

    def notLending(self, cur, minRate, actRate):
        if self.compactLog:
            self.output.statusValue(cur, 'log',
                                    '{:s} Not lending due to rate below {:.4f}% (actual: {:.4f}%)'
                                    .format(self.timestamp(), (minRate * 100), (actRate * 100)))
        else:
            self.log('Not lending {:s} due to rate below {:.4f}% (actual: {:.4f}%)'
                     .format(cur, (minRate * 100), (actRate * 100)))

        self.refreshStatus()

    def refreshStatus(self, lent='', days_remaining=''):
        if lent != '':
            self._lent = lent
        if days_remaining != '':
            self._daysRemaining = days_remaining
        self.output.status(self._lent, self.timestamp(), self._daysRemaining)

    def addSectionLog(self, section, key, value):
        self.output.addSectionLog(section, key, value)

    def updateStatusValue(self, coin, key, value):
        self.output.statusValue(coin, key, value)

    def updateOutputCurrency(self, key, value):
        self.output.outputCurrency(key, value)

    def persistStatus(self):
        self.output.writeJsonFile()
        self.output.clearStatusValues()

    @staticmethod
    def digestApiMsg(msg):
        m = ""
        try:
            m = (msg['message'])
        except KeyError:
            pass
        try:
            m = (msg['error'])
        except KeyError:
            pass
        return m

    @staticmethod
    def notify(msg, notify_conf):
        if notify_conf['enable_notifications']:
            send_notification(msg, notify_conf)
