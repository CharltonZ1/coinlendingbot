#!/bin/env python3

import click
import logging
import logging.config
import sys
import time
import traceback
from decimal import Decimal
from http.client import BadStatusLine
from urllib.error import URLError

import coinlendingbot.Configuration as Config
import coinlendingbot.Data as Data
import coinlendingbot.Lending as Lending
import coinlendingbot.MaxToLend as MaxToLend
from coinlendingbot.Logger import Logger
import coinlendingbot.PluginsManager as PluginsManager
from coinlendingbot.ExchangeApiFactory import ExchangeApiFactory
from coinlendingbot.ExchangeApi import ApiError
import coinlendingbot.WebServer as WebServer


@click.command()
@click.option(
    '-c', '--config', default='default.cfg',
    type=click.File(),
    help='Location of custom configuration file, overrides settings below (Default: default.cfg)'
)
@click.option(
    '-l', '--logconfig', default='logging.ini',
    type=click.File(),
    help='Location of logging configuration file (Defaulr: logging.ini)'
)
@click.option(
    '-d', '--dryrun',
    is_flag=True,
    help='Do not execute orders'
)
def main(config, logconfig, dryrun):
    logging.config.fileConfig(logconfig)
    logger = logging.getLogger('main')
    logger.debug('config: {}, logconfig: {}, dryrun: {}'.format(config, logconfig, dryrun))

    Config.init(config)

    output_currency = Config.get('BOT', 'outputCurrency', 'BTC')
    end_date = Config.get('BOT', 'endDate')
    exchange = Config.get_exchange()

    json_output_enabled = Config.has_option('BOT', 'jsonfile') and Config.has_option('BOT', 'jsonlogsize')
    jsonfile = Config.get('BOT', 'jsonfile', '')

    # Configure web server
    web_server_enabled = Config.getboolean('BOT', 'startWebServer')
    if web_server_enabled:
        logger.info('Web server enabled.')
        if json_output_enabled is False:
            # User wants webserver enabled. Must have JSON enabled. Force logging with defaults.
            json_output_enabled = True
            jsonfile = Config.get('BOT', 'jsonfile', 'www/botweblog.json')
        WebServer.initialize_web_server(Config)

    # Configure logging to display on webpage
    weblog = Logger(jsonfile, Decimal(Config.get('BOT', 'jsonlogsize', 200)), exchange)

    welcome = 'Welcome to {} on {}'.format(Config.get("BOT", "label", "Lending Bot"), exchange)
    logger.info(welcome)
    weblog.log(welcome)

    # initialize the remaining stuff
    api = ExchangeApiFactory.createApi(exchange, Config, weblog)
    MaxToLend.init(Config, weblog)
    Data.init(api, weblog)
    Config.init(config, Data)
    notify_conf = Config.get_notification_config()
    if Config.has_option('MarketAnalysis', 'analyseCurrencies'):
        logger.info('MarketAnalysis enabled.')
        from coinlendingbot.MarketAnalysis import MarketAnalysis
        # Analysis.init(Config, api, Data)
        analysis = MarketAnalysis(Config, api)
        analysis.run()
    else:
        analysis = None
    Lending.init(Config, api, weblog, Data, MaxToLend, dryrun, analysis, notify_conf)

    # load plugins
    PluginsManager.init(Config, api, weblog, notify_conf)

    try:
        while True:
            try:
                logger.info('New round.')
                Data.update_conversion_rates(output_currency, json_output_enabled)
                PluginsManager.before_lending()
                Lending.transfer_balances()
                Lending.cancel_all()
                Lending.lend_all()
                PluginsManager.after_lending()
                weblog.refreshStatus(Data.stringify_total_lent(*Data.get_total_lent()),
                                     Data.get_max_duration(end_date, "status"))
                weblog.persistStatus()
                logger.info('Round finished.')
                time.sleep(Lending.get_sleep_time())
            except KeyboardInterrupt:
                # allow existing the main bot loop
                raise
            except Exception as ex:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                logger.debug(ex)
                logger.debug(repr(traceback.format_tb(exc_traceback)))
                weblog.log_error(ex.message)
                weblog.persistStatus()
                if 'Invalid API key' in ex.message:
                    logger.critical("!!! Troubleshooting !!! Are your API keys correct? No quotation. Just plain keys.")
                    exit(1)
                elif 'Nonce must be greater' in ex.message:
                    logger.critical("!!! Troubleshooting !!! Are you reusing the API key in multiple applications? "
                                    + "Use a unique key for every application.")
                    exit(1)
                elif 'Permission denied' in ex.message:
                    logger.critical("!!! Troubleshooting !!! Are you using IP filter on the key?")
                    exit(1)
                elif 'timed out' in ex.message:
                    logger.warn("Timed out, will retry in " + str(Lending.get_sleep_time()) + "sec")
                elif isinstance(ex, BadStatusLine):
                    logger.warn("Caught BadStatusLine exception from Poloniex, ignoring.")
                elif 'Error 429' in ex.message:
                    additional_sleep = max(130.0-Lending.get_sleep_time(), 0)
                    sum_sleep = additional_sleep + Lending.get_sleep_time()
                    msg = 'IP has been banned due to many requests. Sleeping for {} seconds'.format(sum_sleep)
                    weblog.log_error(msg)
                    logger.warn(msg)
                    if Config.has_option('MarketAnalysis', 'analyseCurrencies'):
                        if api.req_period <= api.default_req_period * 1.5:
                            api.req_period += 3
                        logger.warn("Caught ERR_RATE_LIMIT, sleeping capture and increasing request delay. Current"
                                    + " {0}ms".format(api.req_period))
                        weblog.log_error('Expect this 130s ban periodically when using MarketAnalysis, '
                                         + 'it will fix itself')
                    time.sleep(additional_sleep)
                # Ignore all 5xx errors (server error) as we can't do anything about it (https://httpstatuses.com/)
                elif isinstance(ex, URLError):
                    logger.error("Caught {0} from exchange, ignoring.".format(ex.message))
                elif isinstance(ex, ApiError):
                    logger.error("Caught {0} reading from exchange API, ignoring.".format(ex.message))
                else:
                    logger.error(traceback.format_exc())
                    logger.error("v{0} Unhandled error, please open a Github issue so we can fix it!"
                                 .format(Data.get_bot_version()))
                    if notify_conf['notify_caught_exception']:
                        weblog.notify("{0}\n-------\n{1}".format(ex, traceback.format_exc()), notify_conf)
                time.sleep(Lending.get_sleep_time())

    except KeyboardInterrupt:
        if web_server_enabled:
            WebServer.stop_web_server()
        PluginsManager.on_bot_exit()
        weblog.log('bye')
        logger.info('bye')


if __name__ == '__main__':
    main()
