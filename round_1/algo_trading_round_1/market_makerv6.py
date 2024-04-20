from typing import List
import string
import numpy as np
import json
from typing import Any
import math

import json
from typing import Any
from datamodel import *


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing["symbol"], listing["product"], listing["denomination"]])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sunlight,
                observation.humidity,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()


class Trader:
    # definite init state
    def __init__(self):
        self.orders = {}
        self.conversions = 0
        self.traderData = "SAMPLE"

        self.am_buy_orders = 0
        self.am_sell_orders = 0
        self.am_position = 0

        self.sf_buy_orders = 0
        self.sf_sell_orders = 0
        self.sf_position = 0

    # define easier sell and buy order functions
    def send_sell_order(self, product, price, amount, msg=None):
        self.orders[product].append(Order(product, price, amount))

        if msg is not None:
            logger.print(msg)

    def send_buy_order(self, product, price, amount, msg=None):
        self.orders[product].append(Order(product, price, amount))

        if msg is not None:
            logger.print(msg)

    def printStuff(self, state):
        logger.print("traderData: " + state.traderData)
        logger.print("Observations: " + str(state.observations))

    # Buys things if there are asks below or equal acceptable price
    def search_buys(self, state, product, acceptable_price, depth=1):
        order_depth = state.order_depths[product]
        if len(order_depth.sell_orders) != 0:
            orders = list(order_depth.sell_orders.items())
            for ask, amount in orders[0 : max(len(orders), depth)]:
                # get position
                if product == "AMETHYSTS":
                    pos = self.am_position
                elif product == "STARFRUIT":
                    pos = self.sf_position
                    # market taking                                     market neutralizing
                if int(ask) < acceptable_price or (int(ask) == acceptable_price and (pos < 0 and abs(pos - amount) < abs(pos))):

                    if product == "AMETHYSTS":
                        size = min(20 - self.am_position - self.am_buy_orders, -amount)

                        self.am_buy_orders += size
                        self.send_buy_order(product, ask, size, msg=f"TRADE BUY {str(size)} x @ {ask}")
                    else:
                        size = min(20 - self.sf_position - self.sf_buy_orders, -amount)

                        self.sf_buy_orders += size
                        self.send_buy_order(product, ask, size, msg=f"TRADE BUY {str(size)} x @ {ask}")

    def search_sells(self, state, product, acceptable_price, depth=1):
        order_depth = state.order_depths[product]
        if len(order_depth.buy_orders) != 0:
            orders = list(order_depth.buy_orders.items())
            for bid, amount in orders[0 : max(len(orders), depth)]:

                if product == "AMETHYSTS":
                    pos = self.am_position
                elif product == "STARFRUIT":
                    pos = self.sf_position
                if int(bid) > acceptable_price or (int(bid) == acceptable_price and (pos > 0 and abs(pos - amount) < abs(pos))):
                    if product == "AMETHYSTS":
                        size = min(self.am_position + 20, amount)
                        self.am_sell_orders += size

                        self.send_sell_order(product, bid, -size, msg=f"TRADE SELL {str(-size)} x @ {bid}")
                    else:
                        size = min(self.sf_position + 20, amount)
                        self.sf_sell_orders += size

                        self.send_sell_order(product, bid, -size, msg=f"TRADE SELL {str(-size)} x @ {bid}")

    def get_bid(self, state, product, price):
        order_depth = state.order_depths[product]
        if len(order_depth.buy_orders) != 0:
            orders = list(order_depth.buy_orders.items())
            for bid, _ in orders:
                if bid < price:  # DONT COPY SHIT MARKETS
                    return bid

        return None

    def get_ask(self, state, product, price):
        order_depth = state.order_depths[product]
        if len(order_depth.sell_orders) != 0:
            orders = list(order_depth.sell_orders.items())
            for ask, _ in orders:
                if ask > price:  # DONT COPY A SHITY MARKET
                    return ask

        return None

    def get_second_bid(self, state, product):
        order_depth = state.order_depths[product]
        if len(order_depth.buy_orders) != 0:
            orders = list(order_depth.buy_orders.items())
            if len(orders) < 2:
                return None
            else:
                bid, _ = orders[1]
                return bid

        return None

    def get_second_ask(self, state, product):
        order_depth = state.order_depths[product]
        if len(order_depth.sell_orders) != 0:
            orders = list(order_depth.sell_orders.items())
            if len(orders) < 2:
                return None
            else:
                ask, _ = orders[1]
                return ask

        return None

    def make_amethysts_market(self, state):

        # Buy anything at a good price
        self.search_buys(state, "AMETHYSTS", 10000, depth=3)
        self.search_sells(state, "AMETHYSTS", 10000, depth=3)

        # Check if there's another market maker
        best_ask = self.get_ask(state, "AMETHYSTS", 10000)
        best_bid = self.get_bid(state, "AMETHYSTS", 10000)

        # our ordinary market
        buy_price = 9996
        sell_price = 10004

        # update market if someone else is better than us
        if best_ask is not None and best_bid is not None:
            ask = best_ask
            bid = best_bid

            sell_price = ask - 1
            buy_price = bid + 1

        max_buy = 20 - self.am_position - self.am_buy_orders
        max_sell = self.am_position + 20 - self.am_sell_orders

        self.send_sell_order("AMETHYSTS", sell_price, -max_sell, msg=f"AMETHYSTS: MARKET MADE Sell {max_sell} @ {sell_price}")
        self.send_buy_order("AMETHYSTS", buy_price, max_buy, msg=f"AMETHYSTS: MARKET MADE Buy {max_buy} @ {buy_price}")

    def make_starfruits_market(self, state):
        low = -20
        high = 20

        position = state.position.get("STARFRUIT", 0)

        max_buy = high - position
        max_sell = position - low

        order_book = state.order_depths["STARFRUIT"]
        sell_orders = order_book.sell_orders
        buy_orders = order_book.buy_orders

        if len(sell_orders) != 0 and len(buy_orders) != 0:
            ask, _ = list(sell_orders.items())[-1]  # worst ask
            bid, _ = list(buy_orders.items())[-1]  # worst bid

            fair_price = int(math.ceil((ask + bid) / 2))

            logger.print(f"Starfruit FAIR PRICE: {fair_price}")
            self.search_buys(state, "STARFRUIT", fair_price, depth=3)
            self.search_sells(state, "STARFRUIT", fair_price, depth=3)

            # Check if there's another market maker
            best_ask = self.get_ask(state, "STARFRUIT", fair_price)
            best_bid = self.get_bid(state, "STARFRUIT", fair_price)

            # our ordinary market
            buy_price = fair_price - 2
            sell_price = fair_price + 2

            # update market if someone else is better than us
            if best_ask is not None and best_bid is not None:
                ask = best_ask
                bid = best_bid

                sell_price = ask - 1
                buy_price = bid + 1

            max_buy = 20 - self.sf_position - self.sf_buy_orders  # MAXIMUM SIZE OF MARKET ON BUY SIDE
            max_sell = self.sf_position + 20 - self.sf_sell_orders  # MAXIMUM SIZE OF MARKET ON SELL SIDE

            self.send_buy_order("STARFRUIT", buy_price, max_buy, msg=f"Starfruit: MARKET MADE Buy {max_buy} @ {buy_price}")
            self.send_sell_order("STARFRUIT", sell_price, -max_sell, msg=f"Starfruit: MARKET MADE Sell {max_sell} @ {sell_price}")

    def run(self, state: TradingState):
        self.orders = {}
        self.conversions = 0

        self.am_position = state.position.get("AMETHYSTS", 0)
        self.am_buy_orders = 0
        self.am_sell_orders = 0

        self.sf_position = state.position.get("STARFRUIT", 0)
        self.sf_buy_orders = 0
        self.sf_sell_orders = 0

        for product in state.order_depths:
            self.orders[product] = []

        self.make_amethysts_market(state)
        self.make_starfruits_market(state)

        logger.flush(state, self.orders, self.conversions, self.traderData)
        return self.orders, self.conversions, self.traderData
