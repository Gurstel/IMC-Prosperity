from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import math
import numpy as np


class Trader:
    def __init__(self):
        self.amethysts_stable_price = 10000
        self.starfruit_predicted_price = 5051.31
        self.recent_starfruit_prices = [5051.31] * 30
        self.amethysts_order_quantity = 3
        self.starfruit_order_quantity = 3
        self.starfruit_price_buffer = 1.7
        self.starfruit_long_term_mean = 5037.43
        self.deviation_threshold = 16
        self.position_limits = {"AMETHYSTS": 20, "STARFRUIT": 20}
        self.current_positions = {"AMETHYSTS": 0, "STARFRUIT": 0}

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

    def can_place_order(self, product, quantity):
        future_position = self.current_positions.get(product, 0) + quantity
        return abs(future_position) <= self.position_limits[product]

    def update_positions(self, product, quantity):
        if product in self.current_positions:
            self.current_positions[product] += quantity
        else:
            self.current_positions[product] = quantity

    def run(self, state):
        orders = {}
        for product in state.order_depths:
            if product == "AMETHYSTS":  # Gets 302 seashells
                orders[product] = self.trade_amethysts(state.order_depths[product])
            # elif product == "STARFRUIT":  # Gets 358.4 seashells
            #     new_price = self.get_recent_starfruit_price(state)
            #     self.update_starfruit_prediction(new_price)
            #     orders[product] = self.trade_starfruit(
            #         state.order_depths[product], new_price
            #     )

        conversions = 0
        traderData = "SAMPLE"
        return orders, conversions, traderData

    def trade_amethysts(self, order_depth):
        orders = []
        best_bid_price = max(
            order_depth.buy_orders.keys(), default=self.amethysts_stable_price
        )
        best_ask_price = min(
            order_depth.sell_orders.keys(), default=self.amethysts_stable_price
        )
        buy_price = int(min(best_bid_price, self.amethysts_stable_price - 2))
        sell_price = int(max(best_ask_price, self.amethysts_stable_price + 2))

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
        current_price_deviation = new_price - self.starfruit_long_term_mean

        # Use order depth to determine current best bid and ask prices
        best_bid_price = (
            max(order_depth.buy_orders.keys(), default=new_price)
            if order_depth.buy_orders
            else new_price
        )
        best_ask_price = (
            min(order_depth.sell_orders.keys(), default=new_price)
            if order_depth.sell_orders
            else new_price
        )

        if abs(current_price_deviation) > self.deviation_threshold:
            confidence_level = abs(current_price_deviation) / self.deviation_threshold
            adjusted_quantity = max(
                1, int(self.starfruit_order_quantity * confidence_level)
            )

            if current_price_deviation > 0:
                # If price is above the long-term mean, consider it overbought and prepare to sell
                sell_price = int(
                    min(new_price - self.starfruit_price_buffer, best_ask_price - 1)
                )
                if self.can_place_order("STARFRUIT", -adjusted_quantity):
                    orders.append(
                        {
                            "symbol": "STARFRUIT",
                            "price": sell_price,
                            "quantity": -adjusted_quantity,
                        }
                    )
            else:
                # If price is below the long-term mean, consider it oversold and prepare to buy
                buy_price = int(
                    max(new_price + self.starfruit_price_buffer, best_bid_price + 1)
                )
                if self.can_place_order("STARFRUIT", adjusted_quantity):
                    orders.append(
                        {
                            "symbol": "STARFRUIT",
                            "price": buy_price,
                            "quantity": adjusted_quantity,
                        }
                    )
        else:
            # When current price is close to the long-term mean, engage in regular trading strategy
            buy_price = int(
                max(new_price + self.starfruit_price_buffer, best_bid_price + 1)
            )
            sell_price = int(
                min(new_price - self.starfruit_price_buffer, best_ask_price - 1)
            )

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
