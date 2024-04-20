from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import math  # Import math for rounding

# GETS 147 SEASHELLS


class Trader:

    def __init__(self):
        self.base_spread = 4.74
        self.max_position = 20

    def calculate_spread(self, current_mid_price):
        spread_adjustment = current_mid_price * 0.0005
        return max(self.base_spread, spread_adjustment)

    def maximize_order_size(self, current_position):
        """Calculate the maximum order size based on current position to swing to the extremes."""
        if current_position >= 0:
            # If currently long or neutral, prepare to swing to max short position
            return -self.max_position - current_position
        else:
            # If currently short, prepare to swing to max long position
            return self.max_position - abs(current_position)

    def run(self, state: TradingState):
        result = {}
        product = "AMETHYSTS"

        if product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders = []

            if order_depth.buy_orders and order_depth.sell_orders:
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                mid_price = (best_bid + best_ask) / 2

                spread = self.calculate_spread(mid_price)

                bid_price = math.floor(mid_price - spread / 2)
                ask_price = math.ceil(mid_price + spread / 2)

                current_position = state.position.get(product, 0)
                order_size = self.maximize_order_size(current_position)

                if current_position + order_size <= self.max_position:
                    orders.append(Order(product, bid_price, order_size))
                if current_position - order_size >= -self.max_position:
                    orders.append(Order(product, ask_price, -order_size))

            result[product] = orders

        traderData = "Updated state or info you want to track"
        conversions = 0
        return result, conversions, traderData
