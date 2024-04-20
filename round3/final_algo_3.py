from datamodel import *
from typing import List
import string
import numpy as np
import json
from typing import Any

import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Any
import math


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

        # new inits
        self.basket_buys = 0
        self.basket_sells = 0
        self.POS_LIMIT_CHOCOLATE = 250
        self.POS_LIMIT_STRAWBERRIES = 350
        self.POS_LIMIT_ROSES = 60
        self.POS_LIMIT_GIFT_BASKET = 58  # reduce by 2 to help.

        self.arb_positions = {}

        self.all_b = []
        self.window_size = 1000
        self.premium = 375

        self.basket_buy_orders = 0
        self.basket_sell_orders = 0

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

    def get_all_mid_prices(self, state):
        midprices = dict()
        for product in state.order_depths:
            order_book = state.order_depths[product]
            if product in ["CHOCOLATE", "ROSES", "STRAWBERRIES", "GIFT_BASKET"]:
                sell_orders = order_book.sell_orders
                buy_orders = order_book.buy_orders

                ask, _ = list(sell_orders.items())[0]
                bid, _ = list(buy_orders.items())[0]

                mid_price = (ask + bid) / 2

                midprices[product] = mid_price

        return midprices

    def get_best_ask(self, state, product):
        order_book = state.order_depths[product]
        sell_orders = order_book.sell_orders
        ask, amount = list(sell_orders.items())[0]
        return ask, amount

    def get_best_bid(self, state, product):
        order_book = state.order_depths[product]
        buy_orders = order_book.buy_orders
        bid, amount = list(buy_orders.items())[0]
        return bid, amount

    def calculate_long_arbitrage(self, state):
        chocolate, _ = self.get_best_bid(state, "CHOCOLATE")
        strawberries, _ = self.get_best_bid(state, "STRAWBERRIES")
        roses, _ = self.get_best_bid(state, "ROSES")
        baskets, _ = self.get_best_ask(state, "GIFT_BASKET")

        premium = 375
        long_arb = baskets - premium - chocolate * 4 - strawberries * 6 - roses
        return long_arb * -1  # long arb is negative when there's profit

    def calculate_short_arbitrage(self, state):
        chocolate, _ = self.get_best_ask(state, "CHOCOLATE")
        strawberries, _ = self.get_best_ask(state, "STRAWBERRIES")
        roses, _ = self.get_best_ask(state, "ROSES")
        baskets, _ = self.get_best_bid(state, "GIFT_BASKET")

        premium = 375
        short_arb = baskets - premium - chocolate * 4 - strawberries * 6 - roses
        return short_arb

    def enter_long_on_basket_pair(self, state, limit=60, hedge=False, short_underlying=False):
        # prices
        chocolate_best_bid, choc_amount = self.get_best_bid(state, "CHOCOLATE")
        strawberries_best_bid, straw_amount = self.get_best_bid(state, "STRAWBERRIES")
        roses_best_bid, roses_amount = self.get_best_bid(state, "ROSES")
        basket_best_ask, basket_amount = self.get_best_ask(state, "GIFT_BASKET")

        # sizes
        basket_pos = state.position.get("GIFT_BASKET", 0)
        size = min(-1 * basket_amount, abs(limit - basket_pos))
        size = min(size, 16)  # Stagger orders

        choc_size = min(choc_amount, size * 4)
        strawberry_size = min(straw_amount, size * 6)
        roses_size = min(roses_amount, size)

        if short_underlying and not hedge:
            # orders
            logger.print("Shorting Underlying")
            self.send_sell_order("CHOCOLATE", chocolate_best_bid, -choc_size)
            self.send_sell_order("STRAWBERRIES", strawberries_best_bid, -strawberry_size)
            self.send_sell_order("ROSES", roses_best_bid, -roses_size)
        else:
            self.send_buy_order("GIFT_BASKET", basket_best_ask, size, msg=f"\tBuying {size} Baskets @ {basket_best_ask}")

        if hedge:
            # orders
            self.send_sell_order("CHOCOLATE", chocolate_best_bid, -choc_size)
            self.send_sell_order("STRAWBERRIES", strawberries_best_bid, -strawberry_size)
            self.send_sell_order("ROSES", roses_best_bid, -roses_size)

    def enter_short_on_basket_pair(self, state, limit=60, hedge=False, long_underlying=False):
        # prices
        chocolate_best_ask, choc_amount = self.get_best_ask(state, "CHOCOLATE")
        strawberries_best_ask, straw_amount = self.get_best_ask(state, "STRAWBERRIES")
        roses_best_ask, roses_amount = self.get_best_ask(state, "ROSES")
        basket_best_bid, basket_amount = self.get_best_bid(state, "GIFT_BASKET")

        # sizes
        basket_pos = state.position.get("GIFT_BASKET", 0)
        size = min(abs(basket_amount), limit + basket_pos)
        size = min(size, 16)  # Stagger orders

        choc_size = min(-1 * choc_amount, size * 4)
        strawberry_size = min(-1 * straw_amount, size * 6)
        roses_size = min(-1 * roses_amount, size)

        if long_underlying and not hedge:
            # orders
            logger.print("Buying Underlying")
            self.send_buy_order("CHOCOLATE", chocolate_best_ask, choc_size)
            self.send_buy_order("STRAWBERRIES", strawberries_best_ask, strawberry_size)
            self.send_buy_order("ROSES", roses_best_ask, roses_size)
        else:
            self.send_sell_order("GIFT_BASKET", basket_best_bid, -size, msg="Sell Baskets")

        if hedge:
            # orders
            self.send_buy_order("CHOCOLATE", chocolate_best_ask, choc_size)
            self.send_buy_order("STRAWBERRIES", strawberries_best_ask, strawberry_size)
            self.send_buy_order("ROSES", roses_best_ask, roses_size)

    def close_hedge(self, state, long=True):
        # if im in a long hedge, that means I've sold the the products. So I want to buy them back.
        choc_pos = state.position.get("CHOCOLATE", 0)
        straw_pos = state.position.get("STRAWBERRIES", 0)
        roses_pos = state.position.get("ROSES", 0)

        # prices, long or short
        if long:
            choc_price, choc_amount = self.get_best_ask(state, "CHOCOLATE")
            straw_price, straw_amount = self.get_best_ask(state, "STRAWBERRIES")
            roses_price, roses_amount = self.get_best_ask(state, "ROSES")
        else:
            choc_price, choc_amount = self.get_best_bid(state, "CHOCOLATE")
            straw_price, straw_amount = self.get_best_bid(state, "STRAWBERRIES")
            roses_price, roses_amount = self.get_best_bid(state, "ROSES")

        # sizes
        choc_size = min(abs(choc_amount), abs(choc_pos))
        strawberry_size = min(abs(straw_amount), abs(straw_pos))
        roses_size = min(abs(roses_amount), abs(roses_pos))

        # orders, long or short
        if long:
            logger.print("Checking to remove Short Position on Underlying")
            self.send_buy_order("CHOCOLATE", choc_price, choc_size)
            self.send_buy_order("STRAWBERRIES", straw_price, strawberry_size)
            self.send_buy_order("ROSES", roses_price, roses_size)

        else:
            logger.print("Checking to remove Long Position on Underlying")
            self.send_sell_order("CHOCOLATE", choc_price, -choc_size)
            self.send_sell_order("STRAWBERRIES", straw_price, -strawberry_size)
            self.send_sell_order("ROSES", roses_price, -roses_size)

    def trade_baskets(self, state):
        # long arb will be positive if there is an arb opportunity!
        long_arb_premium = self.calculate_long_arbitrage(state)
        short_arb_premium = self.calculate_short_arbitrage(state)

        logger.print(f"Long Arb Premium: {long_arb_premium}")
        logger.print(f"Short Arb Premium: {short_arb_premium}")

        # dynamic position sizing
        basket_position = state.position.get("GIFT_BASKET", 0)

        in_long = basket_position > 0
        in_short = basket_position < 0

        self.basket_buy_orders = 0
        self.basket_sell_orders = 0

        # close our short hedge if we have one
        if short_arb_premium > 20 and in_short:
            self.close_hedge(state, long=False)

        # close our long hedge if we have one
        elif long_arb_premium > 20 and in_long:
            self.close_hedge(state, long=True)

        # (signal, limit, hedge)
        buy_combos = [(65, 60, False), (10, 59, False)]

        sell_combos = [(208, 60, False), (153, 60, False), (99, 60, False), (44, 60, False)]

        # calculate premium as a percentage of price

        for level, limit, hedge in buy_combos:
            if long_arb_premium > level:
                logger.print(f"\nEntering Long on Basket \n\tPremium: {long_arb_premium} \n\tLimit: {limit} \n\tHedge: {hedge}")
                self.enter_long_on_basket_pair(state, limit=limit, hedge=hedge)
                break

        for level, limit, hedge in sell_combos:
            if short_arb_premium > level:
                logger.print(f"Entering Long on Basket \n\tPremium: {short_arb_premium} \n\tLimit Size: {limit} \n\tHedge: {hedge}")
                self.enter_short_on_basket_pair(state, limit=limit, hedge=hedge)
                break

    def run(self, state: TradingState):
        self.orders = {}
        self.conversions = 0

        self.basket_sells = 0
        self.basket_buys = 0

        for product in state.order_depths:
            self.orders[product] = []

        self.trade_baskets(state)

        logger.flush(state, self.orders, self.conversions, self.traderData)
        return self.orders, self.conversions, self.traderData
