from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import math
import numpy as np


class Trader:
    def __init__(self):
        self.amethysts_stable_price = 10000
        self.starfruit_predicted_price = (
            5051.31  # Initial placeholder, will be dynamically updated
        )
        self.recent_starfruit_prices = [
            5051.31
        ] * 30  # Initialize with historical prediction value
        self.amethysts_order_quantity = 3  # Based on average trade size analysis
        self.starfruit_order_quantity = (
            3  # Based on average trade size and volatility analysis
        )
        self.starfruit_price_buffer = 1.7  # Set around the volatility measure

    def update_starfruit_prediction(self, new_price: float):
        self.recent_starfruit_prices.append(new_price)
        if len(self.recent_starfruit_prices) > 30:
            self.recent_starfruit_prices.pop(0)

        prices = np.array(self.recent_starfruit_prices)
        time_steps = np.arange(len(prices))

        N = len(prices)
        sum_x = np.sum(time_steps)
        sum_y = np.sum(prices)
        sum_xy = np.sum(time_steps * prices)
        sum_x_squared = np.sum(time_steps**2)

        m = (N * sum_xy - sum_x * sum_y) / (N * sum_x_squared - sum_x**2)
        b = (sum_y - m * sum_x) / N

        self.starfruit_predicted_price = m * (len(prices)) + b

    def get_recent_starfruit_price(self, state: "TradingState") -> float:
        if "STARFRUIT" in state.own_trades and state.own_trades["STARFRUIT"]:
            return state.own_trades["STARFRUIT"][-1].price
        elif "STARFRUIT" in state.market_trades and state.market_trades["STARFRUIT"]:
            return state.market_trades["STARFRUIT"][-1].price
        if "STARFRUIT" in state.order_depths:
            order_depth = state.order_depths["STARFRUIT"]
            if order_depth.sell_orders and order_depth.buy_orders:
                best_ask = min(order_depth.sell_orders.keys())
                best_bid = max(order_depth.buy_orders.keys())
                return (best_ask + best_bid) / 2
        return self.starfruit_predicted_price

    def update_positions(self, product, quantity):
        # Update current positions after placing orders
        if product in self.current_positions:
            self.current_positions[product] += quantity
        else:
            self.current_positions[product] = quantity

    def can_place_order(self, product, quantity):
        # Check if placing the order exceeds position limits
        if product not in self.position_limits:
            return False
        future_position = self.current_positions.get(product, 0) + quantity
        return abs(future_position) <= self.position_limits[product]

    def run(self, state):
        orders = {}
        for product in state.order_depths:
            if product == "AMETHYSTS":
                orders[product] = self.trade_amethysts(state.order_depths[product])
            elif product == "STARFRUIT":
                new_price = self.get_recent_starfruit_price(state)
                self.update_starfruit_prediction(new_price)
                orders[product] = self.trade_starfruit(
                    state.order_depths[product], new_price
                )

        conversions = 0
        traderData = "SAMPLE"
        return orders, conversions, traderData

    def trade_amethysts(self, order_depth):
        orders = []
        # For AMETHYSTS, consider adjusting the buy and sell prices based on the order depth
        best_bid_price = max(
            order_depth["buy_orders"].keys(), default=self.amethysts_stable_price
        )
        best_ask_price = min(
            order_depth["sell_orders"].keys(), default=self.amethysts_stable_price
        )

        buy_price = min(best_bid_price + 1, self.amethysts_stable_price - 1)
        sell_price = max(best_ask_price - 1, self.amethysts_stable_price + 1)

        if self.can_place_order("AMETHYSTS", self.amethysts_order_quantity):
            orders.append(
                {
                    "symbol": "AMETHYSTS",
                    "price": buy_price,
                    "quantity": self.amethysts_order_quantity,
                }
            )

        if self.can_place_order("AMETHYSTS", -self.amethysts_order_quantity):
            orders.append(
                {
                    "symbol": "AMETHYSTS",
                    "price": sell_price,
                    "quantity": -self.amethysts_order_quantity,
                }
            )

        return orders

    def trade_starfruit(self, order_depth, new_price):
        orders = []
        # Adjusting strategy based on the new price and prediction model for STARFRUIT
        self.starfruit_predicted_price = (
            new_price  # Assume new_price is the prediction or latest market price
        )

        best_bid_price = max(order_depth["buy_orders"].keys(), default=new_price)
        best_ask_price = min(order_depth["sell_orders"].keys(), default=new_price)

        buy_price = self.starfruit_predicted_price - self.starfruit_price_buffer
        sell_price = self.starfruit_predicted_price + self.starfruit_price_buffer

        # Fine-tune buy and sell prices based on the best available market prices
        buy_price = min(buy_price, best_bid_price + 1)
        sell_price = max(sell_price, best_ask_price - 1)

        if self.can_place_order("STARFRUIT", self.starfruit_order_quantity):
            orders.append(
                {
                    "symbol": "STARFRUIT",
                    "price": buy_price,
                    "quantity": self.starfruit_order_quantity,
                }
            )

        if self.can_place_order("STARFRUIT", -self.starfruit_order_quantity):
            orders.append(
                {
                    "symbol": "STARFRUIT",
                    "price": sell_price,
                    "quantity": -self.starfruit_order_quantity,
                }
            )

        return orders
