from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import math


class Trader:

    def __init__(self):
        self.base_spread = 4.74
        self.max_position = 20
        # Initialize a dictionary to hold rolling historical prices for each product
        self.rolling_prices: Dict[str, List[float]] = {"AMETHYSTS": [], "STARFRUIT": []}
        # Maximum number of historical prices to keep
        self.max_historical_prices = 20

    def calculate_spread(self, current_mid_price):
        spread_adjustment = current_mid_price * 0.0005
        return max(self.base_spread, spread_adjustment)

    def maximize_order_size(self, current_position):
        if current_position >= 0:
            return -self.max_position - current_position
        else:
            return self.max_position - abs(current_position)

    def calculate_moving_average(self, prices):
        if not prices:
            return None
        return sum(prices) / len(prices)

    def update_rolling_prices(self, product, new_price):
        if len(self.rolling_prices[product]) >= self.max_historical_prices:
            # Remove the oldest price if we've reached the max number of historical prices
            self.rolling_prices[product].pop(0)
        # Add the new price
        self.rolling_prices[product].append(new_price)

    def run(self, state: TradingState):
        result = {}

        for product in ["AMETHYSTS", "STARFRUIT"]:
            if product in state.order_depths:
                order_depth: OrderDepth = state.order_depths[product]
                orders = []

                if order_depth.buy_orders and order_depth.sell_orders:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_ask = min(order_depth.sell_orders.keys())
                    mid_price = (best_bid + best_ask) / 2

                    # Update the rolling prices with the latest mid_price
                    self.update_rolling_prices(product, mid_price)

                    spread = self.calculate_spread(mid_price)
                    bid_price = math.floor(mid_price - spread / 2)
                    ask_price = math.ceil(mid_price + spread / 2)
                    current_position = state.position.get(product, 0)

                    if product == "AMETHYSTS":
                        order_size = self.maximize_order_size(current_position)
                        orders.append(
                            Order(
                                product,
                                bid_price if order_size > 0 else ask_price,
                                order_size,
                            )
                        )

                    elif product == "STARFRUIT":
                        # Use the updated rolling prices for STARFRUIT to calculate the moving average
                        long_term_avg = self.calculate_moving_average(
                            self.rolling_prices["STARFRUIT"]
                        )
                        if long_term_avg is not None:
                            if mid_price < long_term_avg:  # Mean reversion buy signal
                                order_size = min(
                                    20 - current_position, self.max_position
                                )
                                orders.append(Order(product, bid_price, order_size))
                            elif (
                                mid_price > long_term_avg
                            ):  # Mean reversion sell signal
                                order_size = max(
                                    -20 - current_position, -self.max_position
                                )
                                orders.append(Order(product, ask_price, order_size))

                result[product] = orders

        traderData = "Updated strategy state with dynamic price history"
        conversions = 0
        return result, conversions, traderData
