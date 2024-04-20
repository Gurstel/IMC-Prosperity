from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import collections
from collections import defaultdict
import random
import math
import copy
import numpy as np
import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Any


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


# 104412
logger = Logger()


class Trader:
    def __init__(self):
        self.conversions = 0
        self.buys = 0
        self.sells = 0

    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        self.conversions = 0
        # Orders to be placed on exchange matching engine
        result = {}
        traderData = "SAMPLE"  # String value holding Trader state data for next execution
        orders: List[Order] = []
        for product in ["ORCHIDS"]:
            if product == "ORCHIDS":
                details = state.observations.conversionObservations.get(product, None)
                if details is None:
                    continue
                if details.importTariff > -2.5 and details.sunlight > 4500 and details.humidity > 95:
                    # Check if there are enough buy orders to match against
                    logger.print("WE ARE SELLING AND IMPORTS ARE LOW")
                    if state.order_depths[product].buy_orders:
                        best_bid_price = max(state.order_depths[product].buy_orders.keys())
                        quantity = state.order_depths[product].buy_orders[best_bid_price]  # Example quantity
                        orders.append(Order(product, best_bid_price, -quantity))  # Negative quantity for selling
                self.trade_orchids(state, orders)
                result[product] = orders

        return result, self.conversions, traderData

    def trade_orchids(self, state, orders):
        product = "ORCHIDS"
        current_position = state.position.get(product, 0)
        logger.print("Current position", current_position)
        if current_position != 0:
            logger.print("Buying from other island: ", abs(current_position), "ORCHIDS")
            self.conversions += -current_position

        if current_position == 0:
            logger.print("We bought ORCHIDS from other island, now looking to sell again")
        observations = state.observations.conversionObservations.get(product, None)
        if observations is None:
            return []
        conversion_ask_price = observations.askPrice
        conversion_bid_price = observations.bidPrice
        import_tariff = observations.importTariff
        export_tariff = observations.exportTariff
        transport_fees = observations.transportFees
        sunlight = observations.sunlight
        humidity = observations.humidity
        buy_orders = state.order_depths[product].buy_orders
        sell_orders = state.order_depths[product].sell_orders
        best_bid = max(buy_orders.keys())
        best_ask = min(sell_orders.keys())

        break_even_sell = conversion_ask_price + import_tariff + transport_fees
        whole_number_sell = conversion_bid_price % 1
        if whole_number_sell == 0:
            potential_sell_price = int(conversion_bid_price - 1)
        else:
            potential_sell_price = math.floor(conversion_bid_price)
        # Sell at a price higher than the break-even point that is below the midpoint
        sell_price = max(math.ceil(break_even_sell), potential_sell_price)
        logger.print("Selling ORCHIDS in own island at", sell_price)
        orders.append(Order(product, sell_price, -100))

        whole_number_buy = conversion_ask_price % 1
        if whole_number_buy == 0:
            potential_buy_price = int(conversion_ask_price + 1)
        else:
            potential_buy_price = math.ceil(conversion_ask_price)
        break_even_buy = conversion_bid_price - export_tariff - transport_fees
        # Buy at a price lower than the break-even point that is above the midpoint
        buy_price = min(math.floor(break_even_buy), potential_buy_price)
        logger.print("Buying ORCHIDS in own island at", buy_price)
        orders.append(Order(product, buy_price, 100))
