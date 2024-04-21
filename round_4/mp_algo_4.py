# Got us to 593.362 during round 2

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
        result = {}
        self.conversions = 0
        for product in ["AMETHYSTS", "STARFRUIT", "ORCHIDS", "GIFT_BASKET", "COCONUT"]:
            if product == "ORCHIDS":
                continue
                orders: List[Order] = []
                self.trade_orchids(state, orders)
                result[product] = orders
            elif product in ["AMETHYSTS", "STARFRUIT"]:
                continue
                self.buys = 0
                self.sells = 0
                orders: List[Order] = []
                order_depth: OrderDepth = state.order_depths[product]
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
            elif product == "GIFT_BASKET":
                continue
                orders: List[Order] = []
                self.trade_baskets(state, orders)
                result["GIFT_BASKET"] = [o for o in orders if o.symbol == "GIFT_BASKET"]
                result["STRAWBERRIES"] = [o for o in orders if o.symbol == "STRAWBERRIES"]
                result["CHOCOLATE"] = [o for o in orders if o.symbol == "CHOCOLATE"]
                result["ROSES"] = [o for o in orders if o.symbol == "ROSES"]
            elif product in ["COCONUT"]:
                orders: List[Order] = []
                self.trade_coupons(state, orders)
                result["COUPON"] = [o for o in orders if o.symbol == "COCONUT"]
                result["COUPON_COUPON"] = [o for o in orders if o.symbol == "COCONUT_COUPON"]

        traderData = "Updated State"  # Update the trader state for next iteration
        logger.flush(state, result, self.conversions, traderData)
        return result, self.conversions, traderData

    def trade_coupons(self, state, orders):
        # 4755 online, cant see backtester for some reason
        coconut_buy_orders = state.order_depths["COCONUT"].buy_orders
        coconut_sell_orders = state.order_depths["COCONUT"].sell_orders
        coupon_buy_orders = state.order_depths["COCONUT_COUPON"].buy_orders
        coupon_sell_orders = state.order_depths["COCONUT_COUPON"].sell_orders
        coconut_position = state.position.get("COCONUT", 0)
        coupon_position = state.position.get("COCONUT_COUPON", 0)
        if(len(coconut_buy_orders.keys()) < 1 or len(coconut_sell_orders.keys()) < 1 
           or len(coupon_sell_orders.keys()) < 1 or len(coupon_buy_orders) < 1): return
        best_coconut_bid, best_coconut_bid_volume = max(coconut_buy_orders.keys()), coconut_buy_orders[max(coconut_buy_orders.keys())]
        best_coconut_ask, best_coconut_ask_volume = min(coconut_sell_orders.keys()), coconut_sell_orders[min(coconut_sell_orders.keys())]
        best_coupon_bid, best_coupon_bid_volume = max(coupon_buy_orders.keys()), coupon_buy_orders[max(coupon_buy_orders.keys())]
        best_coupon_ask, best_coupon_ask_volume = min(coupon_sell_orders.keys()), coupon_sell_orders[min(coupon_sell_orders.keys())]
        coconut_mid_price = (best_coconut_ask + best_coconut_bid) / 2
        coupon_mid_price = (best_coupon_ask + best_coupon_bid) / 2

        converted_coconut_mid_price = self.convert_coconut(coconut_mid_price)
        action_threshold = 5 #Difference in prices signaling to take action
        neutralize_threshold = 1 #Difference in prices signaling to neutralize position
        coupon_limit = 600
        coconut_limit = 300

        difference = abs(converted_coconut_mid_price - coupon_mid_price)
        # logger.print("Difference is:", difference)
        # logger.print("Current positions are (C, CC): ", coconut_position, coupon_position)
        if(difference >= action_threshold):
            #ACTION TIME / FIGURE OUT WHICH TO BUY / SELL
            if(converted_coconut_mid_price > coupon_mid_price):
                # SELL COCONUT, BUY COUPON
                # logger.print("Selling Coconut, buying coupon")
                # logger.print("Buy possibilities: ", best_coupon_bid_volume, coupon_limit - coupon_position)
                # logger.print("Sell possibilities: ", best_coconut_ask_volume, -coconut_limit - coconut_position)
                buy_size = min(best_coupon_bid_volume, coupon_limit - coupon_position)
                sell_size = max(best_coconut_ask_volume, -coconut_limit - coconut_position)
                
                # logger.print("Coconut sell size:", sell_size, "coupon buy size: ", buy_size)
                # logger.print("Coconut sell price:", best_coconut_bid, "Coupon buy price: ", best_coupon_ask)

                orders.append(Order("COCONUT", best_coconut_bid, sell_size))
                orders.append(Order("COCONUT_COUPON", best_coupon_ask, buy_size))
            else:
                # SELL COUPON, BUY COCONUT
                logger.print("Selling coupon, buying coconut")
                logger.print("Buy possibilities: ", best_coconut_bid_volume, coconut_limit - coconut_position)
                logger.print("Sell possibilities: ", best_coupon_ask_volume, -coupon_limit - coupon_position)
                buy_size = min(best_coconut_bid_volume, coconut_limit - coconut_position)
                sell_size = max(best_coupon_ask_volume, -coupon_limit - coupon_position)
                logger.print("Coupon sell size:", sell_size, "Coconut buy size: ", buy_size)
                logger.print("Coupon sell price:", best_coupon_bid, "Coconut buy price: ", best_coconut_ask)
                orders.append(Order("COCONUT_COUPON", best_coupon_bid, sell_size))
                orders.append(Order("COCONUT", best_coconut_ask, buy_size))
        elif (difference <= neutralize_threshold):
            #NEUTRALIZE TIME
            logger.print("Neutralizing position")
            # If we have a positive coconut position, we need to sell coconuts
            if coconut_position > 0:
                # Place an order to sell at the best available ask price, but not more than what we hold
                sell_size = min(coconut_position, best_coconut_bid_volume)
                orders.append(Order("COCONUT", best_coconut_bid, -sell_size))
            elif coconut_position < 0:
                # We have a negative coconut position, so we need to buy coconuts to neutralize
                buy_size = min(-coconut_position, best_coconut_ask_volume)
                orders.append(Order("COCONUT", best_coconut_ask, buy_size))

            # Repeat the same logic for coconut coupons
            if coupon_position > 0:
                # Place an order to sell at the best available ask price, but not more than what we hold
                sell_size = min(coupon_position, best_coupon_bid_volume)
                orders.append(Order("COCONUT_COUPON", best_coupon_bid, -sell_size))
            elif coupon_position < 0:
                # We have a negative coupon position, so we need to buy coupons to neutralize
                buy_size = min(-coupon_position, best_coupon_ask_volume)
                orders.append(Order("COCONUT_COUPON", best_coupon_ask, buy_size))
        

    def trade_baskets(self, state, orders):
        # Total profit: 347,136
        premium = 379
        basket_buy_orders = state.order_depths["GIFT_BASKET"].buy_orders
        basket_sell_orders = state.order_depths["GIFT_BASKET"].sell_orders
        strawberry_buy_orders = state.order_depths["STRAWBERRIES"].buy_orders
        strawberry_sell_orders = state.order_depths["STRAWBERRIES"].sell_orders
        chocolate_buy_orders = state.order_depths["CHOCOLATE"].buy_orders
        chocolate_sell_orders = state.order_depths["CHOCOLATE"].sell_orders
        rose_buy_orders = state.order_depths["ROSES"].buy_orders
        rose_sell_orders = state.order_depths["ROSES"].sell_orders
        best_basket_bid, best_basket_bid_volume = max(basket_buy_orders.keys()), basket_buy_orders[max(basket_buy_orders.keys())]
        best_basket_ask, best_basket_ask_volume = min(basket_sell_orders.keys()), basket_sell_orders[min(basket_sell_orders.keys())]
        best_strawberry_bid, best_strawberry_bid_volume = max(strawberry_buy_orders.keys()), strawberry_buy_orders[max(strawberry_buy_orders.keys())]
        best_strawberry_ask, best_strawberry_ask_volume = min(strawberry_sell_orders.keys()), strawberry_sell_orders[min(strawberry_sell_orders.keys())]
        best_chocolate_bid, best_chocolate_bid_volume = max(chocolate_buy_orders.keys()), chocolate_buy_orders[max(chocolate_buy_orders.keys())]
        best_chocolate_ask, best_chocolate_ask_volume = min(chocolate_sell_orders.keys()), chocolate_sell_orders[min(chocolate_sell_orders.keys())]
        best_rose_bid, best_rose_bid_volume = max(rose_buy_orders.keys()), rose_buy_orders[max(rose_buy_orders.keys())]
        best_rose_ask, best_rose_ask_volume = min(rose_sell_orders.keys()), rose_sell_orders[min(rose_sell_orders.keys())]
        short_arbitrage_premium = best_basket_bid - premium - best_chocolate_ask * 4 - best_strawberry_ask * 6 - best_rose_ask
        long_arbitrage_premium = -(best_basket_ask - premium - best_chocolate_bid * 4 - best_strawberry_bid * 6 - best_rose_bid)
        basket_position = state.position.get("GIFT_BASKET", 0)

        basket_buy_orders = 0
        basket_sell_orders = 0
        # (signal, limit, hedge)
        buy_combos = [(10, 59)]

        sell_combos = [(44, 60)]
        for level, limit in buy_combos:
            if long_arbitrage_premium > level:
                logger.print("BEST BASKET ASK", best_basket_ask_volume)
                size = min(-best_basket_ask_volume, limit - basket_position)

                orders.append(Order("GIFT_BASKET", best_basket_ask, size))
                orders.append(Order("CHOCOLATE", best_chocolate_bid, -size * 4))
                orders.append(Order("STRAWBERRIES", best_strawberry_bid, -size * 6))
                orders.append(Order("ROSES", best_rose_bid, -size))
                break

        for level, limit in sell_combos:
            if short_arbitrage_premium > level:
                size = max(-best_basket_bid_volume, -limit - basket_position)

                orders.append(Order("GIFT_BASKET", best_basket_bid, size))
                orders.append(Order("CHOCOLATE", best_chocolate_ask, size * 4))
                orders.append(Order("STRAWBERRIES", best_strawberry_ask, size * 6))
                orders.append(Order("ROSES", best_rose_ask, size))
                break

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

    def convert_coconut(self, coconut_price):
        return 0.502864795722927*coconut_price - 4393.552801390371

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
