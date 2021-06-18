# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------

import talib.abstract as ta
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter


class Strategy004(IStrategy):

    """
    Strategy 004
    author@: Gerald Lonlas
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy004
    """

    #BUY params
    buy_adx = IntParameter(25, 75, default=55)
    buy_slowadx = IntParameter(20, 50, default=25)
    buy_cci = IntParameter(-100, -50, default=-55)
    buy_fastk_fastd = IntParameter(10, 20, default=18)
    buy_slowfastk_slowfastd = IntParameter(10, 30, default=12)
    buy_mean_volume = DecimalParameter(0.7, 0.8, default=0.768)

    #Buy params enabled
    buy_adx_enabled = CategoricalParameter([True, False], default=True)
    buy_cci_enabled = CategoricalParameter([True, False], default=True)
    
    
    #Sell params
    sell_slowadx = IntParameter(15, 35, default=28)
    sell_fastk_fastd = IntParameter(60, 80, default=68)

    
    #Sell params enabled
    sell_slowadx_enabled = CategoricalParameter([True, False], default=False)


    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
        "0":  0.044,
        "26":  0.031,
        "36":  0.013,
        "60":  0
    }

    # Optimal stoploss designed for the strategy
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.31

    # Optimal timeframe for the strategy
    timeframe = '5m'

    # trailing stoploss
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    # run "populate_indicators" only for new candle
    process_only_new_candles = False

    # Experimental settings (configuration will overide these if set)
    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = False

    # Optional order type mapping
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        """

        # ADX
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['slowadx'] = ta.ADX(dataframe, 35)

        # Commodity Channel Index: values Oversold:<-100, Overbought:>100
        dataframe['cci'] = ta.CCI(dataframe)

        # Stoch
        stoch = ta.STOCHF(dataframe, 5)
        dataframe['fastd'] = stoch['fastd']
        dataframe['fastk'] = stoch['fastk']
        dataframe['fastk-previous'] = dataframe.fastk.shift(1)
        dataframe['fastd-previous'] = dataframe.fastd.shift(1)

        # Slow Stoch
        slowstoch = ta.STOCHF(dataframe, 50)
        dataframe['slowfastd'] = slowstoch['fastd']
        dataframe['slowfastk'] = slowstoch['fastk']
        dataframe['slowfastk-previous'] = dataframe.slowfastk.shift(1)
        dataframe['slowfastd-previous'] = dataframe.slowfastd.shift(1)

        # EMA - Exponential Moving Average
        dataframe['ema5'] = ta.EMA(dataframe, timeperiod=5)

        dataframe['mean-volume'] = dataframe['volume'].mean()

        return dataframe



    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """

        conditions = []
        #Guards and trends
        
        if self.buy_adx_enabled.value:
            conditions.append(
              (dataframe['adx'] > self.buy_adx.value) | 
              (dataframe['slowadx'] > self.buy_slowadx.value)
            )

        if self.buy_cci_enabled.value:
            conditions.append(dataframe['cci'] < self.buy_cci.value)
            
            conditions.append((
                (dataframe['fastk-previous'] < self.buy_fastk_fastd.value) &
                (dataframe['fastd-previous'] < self.buy_fastk_fastd.value) 
                ))
            
            conditions.append((
                (dataframe['slowfastk-previous'] < self.buy_slowfastk_slowfastd.value) &
                (dataframe['slowfastd-previous'] < self.buy_slowfastk_slowfastd.value)
                ))

            conditions.append((dataframe['fastk-previous'] < dataframe['fastd-previous']))

            conditions.append((dataframe['fastk'] > dataframe['fastd']))

            conditions.append((dataframe['mean-volume'] > self.buy_mean_volume.value))

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        conditions = []

        if self.sell_slowadx_enabled.value:
            conditions.append((dataframe['slowadx'] < self.sell_slowadx.value))
        
        conditions.append((dataframe['fastk'] > self.sell_fastk_fastd.value) | (dataframe['fastd'] > self.sell_fastk_fastd.value))

        conditions.append((dataframe['fastk-previous'] < dataframe['fastd-previous']))

        conditions.append((dataframe['close'] > dataframe['ema5']))
    
       
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'] = 1

        return dataframe
