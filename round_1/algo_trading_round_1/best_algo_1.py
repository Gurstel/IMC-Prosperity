# BEST WE'VE SEEN

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


logger = Logger()


class Trader:
    def __init__(self):
        self.buys = 0
        self.sells = 0

    def run(self, state: TradingState):
        result = {}
        for product in ["AMETHYSTS", "STARFRUIT"]:
            self.buys = 0
            self.sells = 0
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            current_position = state.position.get(product, 0)
            logger.print("Processing", product, "with current position", current_position)
            position_limit = 20  # Maximum allowable position (both long and short)
            if product == "AMETHYSTS":
                midpoint = 10000  # Fixed midpoint for AMETHYSTS
                self.process_market_trades(order_depth, orders, midpoint, current_position, position_limit, product)
                self.process_neutral_trades(order_depth, product, orders, midpoint, current_position)
            elif product == "STARFRUIT":
                midpoint = int(math.ceil((max(order_depth.sell_orders) + min(order_depth.buy_orders)) / 2))
                logger.print("STARFRUIT midpoint", midpoint)
                self.process_market_trades(order_depth, orders, midpoint, current_position, position_limit, product)
                self.process_neutral_trades(order_depth, product, orders, midpoint, current_position)
            # Undercutting strategy: finding the next best buy and sell orders to undercut
            next_sell_order = next((price for price in sorted(order_depth.sell_orders) if price > midpoint), None)
            next_buy_order = next((price for price in sorted(order_depth.buy_orders, reverse=True) if price < midpoint), None)

            # Place undercutting orders if applicable
            if next_buy_order:
                undercut_buy_price = next_buy_order + 1
                if current_position <= position_limit:
                    max_buy_quantity = position_limit - current_position - self.buys
                    if max_buy_quantity > 0:
                        orders.append(Order(product, undercut_buy_price, max_buy_quantity))
                        logger.print("Undercutting buy order", product, undercut_buy_price, max_buy_quantity)

            if next_sell_order:
                undercut_sell_price = next_sell_order - 1
                if current_position >= -position_limit:
                    max_sell_quantity = -position_limit - current_position + self.sells
                    logger.print("Sells during market making", self.sells, "Buys during market making", self.buys)
                    if max_sell_quantity < 0:
                        orders.append(Order(product, undercut_sell_price, max_sell_quantity))
                        logger.print("Undercutting sell order", product, undercut_sell_price, max_sell_quantity)

            result[product] = orders

        traderData = "Updated State"  # Update the trader state for next iteration
        conversions = 0  # No conversions requested
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData

    def process_neutral_trades(self, order_depth, product, orders, midpoint, current_position):
        """Specific processing for product to neutralize position at the midpoint."""
        # Neutralizing strategy at the midpoint of 10000
        if midpoint in order_depth.sell_orders and current_position < 0:
            # Neutralize negative position
            neutralize_quantity = -order_depth.sell_orders[midpoint]
            if current_position < 0 and current_position + neutralize_quantity < abs(current_position):
                orders.append(Order(product, midpoint, neutralize_quantity))
                logger.print("Neutralizing buy", neutralize_quantity, "product at midpoint")
                self.buys += neutralize_quantity
                current_position += neutralize_quantity

        if midpoint in order_depth.buy_orders and current_position > 0:
            # Neutralize positive position
            neutralize_quantity = order_depth.buy_orders[midpoint]
            if current_position > 0 and abs(current_position - neutralize_quantity) < current_position:
                orders.append(Order(product, midpoint, -neutralize_quantity))
                logger.print("Neutralizing sell", neutralize_quantity, "product at midpoint")
                self.sells += neutralize_quantity
                current_position -= neutralize_quantity
        return current_position

    def process_market_trades(self, order_depth, orders, midpoint, current_position, position_limit, product):
        """Generic market trade processing for all products."""
        # Buy below the midpoint
        for price, quantity in sorted(order_depth.sell_orders.items()):
            if price < midpoint:
                logger.print("BUYING at", price, "quantity", quantity, "current_position", current_position, "position_limit", position_limit)
                max_buy_quantity = min(-quantity, position_limit - current_position)
                logger.print("MAX BUY COMPARISION", -quantity, position_limit - current_position, max_buy_quantity)
                if max_buy_quantity > 0:
                    orders.append(Order(product, price, max_buy_quantity))
                    self.buys += max_buy_quantity
                    logger.print("Buys", self.buys, "at", price)
                    logger.print("Buying", max_buy_quantity, product, "at", price)
                    current_position += max_buy_quantity

        # Sell above the midpoint
        for price, quantity in sorted(order_depth.buy_orders.items(), reverse=True):
            if price > midpoint:
                max_sell_quantity = min(quantity, position_limit + current_position)
                if max_sell_quantity > 0:
                    orders.append(Order(product, price, -max_sell_quantity))
                    self.sells += max_sell_quantity
                    logger.print("Sells", self.buys, "at", price)
                    logger.print("Selling", max_sell_quantity, product, "at", price)
                    current_position -= max_sell_quantity
        return current_position
