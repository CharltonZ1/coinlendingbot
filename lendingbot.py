# coding=utf-8
import logging
import logging.config
import argparse
import os
import sys
import shutil
import time
import traceback
from decimal import Decimal
from httplib import BadStatusLine
from urllib2 import URLError

import modules.Configuration as Config
import modules.Data as Data
import modules.Lending as Lending
import modules.MaxToLend as MaxToLend
from modules.Logger import Logger
import modules.PluginsManager as PluginsManager
from modules.ExchangeApiFactory import ExchangeApiFactory
from modules.ExchangeApi import ApiError


try:
    open('lendingbot.py', 'r')
except IOError:
    os.chdir(os.path.dirname(sys.argv[0]))  # Allow relative paths

parser = argparse.ArgumentParser()  # Start args.
parser.add_argument("-cfg", "--config", help="Location of custom configuration file, overrides settings below")
parser.add_argument("-logcfg", "--logconfig", help="Location of logging configuration file.")
parser.add_argument("-dry", "--dryrun", help="Make pretend orders", action="store_true")
args = parser.parse_args()  # End args.

# Start handling args.
dry_run = bool(args.dryrun)
if args.config:
    config_location = args.config
else:
    config_location = 'default.cfg'
if args.logconfig:
    logconfig_location = args.logconfig
else:
    logconfig_location = 'logging.ini'
# End handling args.

# Initialize Python logging (console or file)
if not os.path.isfile(logconfig_location):
    shutil.copy('logging.ini.example', logconfig_location)
logging.config.fileConfig(logconfig_location)
logger = logging.getLogger(__name__)

# Config format: Config.get(category, option, default_value=False, lower_limit=False, upper_limit=False)
# A default_value "None" means that the option is required and the bot will not run without it.
# Do not use lower or upper limit on any config options which are not numbers.
# Define the variable from the option in the module where you use it.

Config.init(config_location)

output_currency = Config.get('BOT', 'outputCurrency', 'BTC')
end_date = Config.get('BOT', 'endDate')
exchange = Config.get_exchange()

json_output_enabled = Config.has_option('BOT', 'jsonfile') and Config.has_option('BOT', 'jsonlogsize')
jsonfile = Config.get('BOT', 'jsonfile', '')

# Configure web server
web_server_enabled = Config.getboolean('BOT', 'startWebServer')
if web_server_enabled:
    if json_output_enabled is False:
        # User wants webserver enabled. Must have JSON enabled. Force logging with defaults.
        json_output_enabled = True
        jsonfile = Config.get('BOT', 'jsonfile', 'www/botweblog.json')

    import modules.WebServer as WebServer
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
Config.init(config_location, Data)
notify_conf = Config.get_notification_config()
if Config.has_option('MarketAnalysis', 'analyseCurrencies'):
    from modules.MarketAnalysis import MarketAnalysis
    # Analysis.init(Config, api, Data)
    analysis = MarketAnalysis(Config, api)
    analysis.run()
else:
    analysis = None
Lending.init(Config, api, weblog, Data, MaxToLend, dry_run, analysis, notify_conf)

# load plugins
PluginsManager.init(Config, api, weblog, notify_conf)


try:
    while True:
        try:
            Data.update_conversion_rates(output_currency, json_output_enabled)
            PluginsManager.before_lending()
            Lending.transfer_balances()
            Lending.cancel_all()
            Lending.lend_all()
            PluginsManager.after_lending()
            weblog.refreshStatus(Data.stringify_total_lent(*Data.get_total_lent()),
                                 Data.get_max_duration(end_date, "status"))
            weblog.persistStatus()
            sys.stdout.flush()
            time.sleep(Lending.get_sleep_time())
        except KeyboardInterrupt:
            # allow existing the main bot loop
            raise
        except Exception as ex:
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
                logger.critical("!!! Troubleshooting !!! Are you using IP filter on the key? Maybe your IP changed?")
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
                logger.error(msg)
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
            sys.stdout.flush()
            time.sleep(Lending.get_sleep_time())


except KeyboardInterrupt:
    if web_server_enabled:
        WebServer.stop_web_server()
    PluginsManager.on_bot_exit()
    weblog.log('bye')
    logger.info('bye')
    os._exit(0)  # Ad-hoc solution in place of 'exit(0)' TODO: Find out why non-daemon thread(s) are hanging on exit
