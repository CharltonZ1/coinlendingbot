# Crypto Coin Lending Bot

The Crypto Coin Lending Bot is written in Python 3 and features automatic lending on exchanges Poloniex and Bitfinex.
It will automatically lend all cryptocurrencies found in your lending account.

It uses an advanced lending strategy which will spread offers across the lend book to take advantage of possible spikes
in lending rates.

Forked from [PoloniexLendingBot](https://github.com/BitBotFactory/poloniexlendingbot).

### Features
- Automatically lend your coins on Poloniex and Bitfinex at the highest possible rates, 24 hours a day.
- Configure your own lending strategy! Be aggressive and hold out for a great rate or be conservative and lend often but
at a lower rate, your choice!
- The ability to spread your offers out to take advantage of spikes in the lending rate.
- Withhold lending a percentage of your coins until the going rate reaches a certain threshold to maximize your profits.
- Lock in a high daily rate for a longer period of time period of up to sixty days, all configurable!
- Automatically transfer any funds you deposit (configurable on a coin-by-coin basis) to your lending account instantly
after deposit.
- View a summary of your bot's activities, status, and reports via an easy-to-set-up webpage that you can access from
anywhere!
- Choose any currency to see your profits in, even show how much you are making in USD!
- Select different lending strategies on a coin-by-coin basis.
- Run multiple instances of the bot for multiple accounts easily using multiple config files.
- Configure a date you would like your coins back, and watch the bot make sure all your coins are available to be traded
or withdrawn at the beginning of that day.
- Optimized to run as Docker image.
- Configurable log output.
- Python 3 only. This fork does not support Python 2.
- Use of Bitfinex websocket API.
- And the best feature of all: It is absolutely free!
