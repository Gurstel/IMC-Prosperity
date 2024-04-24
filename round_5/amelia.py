from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import collections
from collections import defaultdict
import random
import math
import copy
import numpy as np
import json
from datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    ProsperityEncoder,
    Symbol,
    Trade,
    TradingState,
)
from typing import Any
from math import fabs, sqrt, exp, floor
import numpy as np
from statistics import NormalDist
import sys


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(
        self,
        state: TradingState,
        orders: dict[Symbol, list[Order]],
        conversions: int,
        trader_data: str,
    ) -> None:
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

    def run(self, state: TradingState):
        # Only method required. It takes all buy and sell orders for all symbols as an input, and outputs a list of orders to be sent
        logger.print(state.traderData)
        traderData = json.loads(state.traderData) if state.traderData else {}
        result = {}
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            if product == "STARFRUIT":
                startfruit_trader_data = self.trade_starfruit(state, order_depth, orders, traderData)
                traderData.update(startfruit_trader_data)
                result["STARFRUIT"] = orders

        newTraderData = json.dumps(traderData)  # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.

        conversions = 0
        logger.flush(state, result, conversions, newTraderData)
        return result, conversions, newTraderData

    def trade_starfruit(self, state, order_depth, orders, traderData):
        prev_midpoint = traderData.get("prev_midpoint")

        prev_orders = state.market_trades.get("STARFRUIT", [])
        worst_buy_price = min(order_depth.buy_orders.keys())
        worst_sell_price = max(order_depth.sell_orders.keys())
        best_buy_price = max(order_depth.buy_orders.keys())
        best_sell_price = min(order_depth.sell_orders.keys())

        midprice = (best_buy_price + best_sell_price) / 2

        if prev_orders and prev_midpoint:
            amelia_buy_trades = [order for order in prev_orders if order.buyer == "Amelia"]
            amelia_sell_trades = [order for order in prev_orders if order.seller == "Amelia"]

            if len(amelia_buy_trades) != 0 and amelia_buy_trades[0].price > prev_midpoint:
                orders.append(Order("STARFRUIT", worst_buy_price, -20))
            elif len(amelia_sell_trades) and amelia_sell_trades[0].price < prev_midpoint:
                orders.append(Order("STARFRUIT", worst_sell_price, 20))

        return {"prev_midpoint": midprice}
