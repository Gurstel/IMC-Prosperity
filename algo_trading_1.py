from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List


class Trader:

    def __init__(self):
        # Initialize any required variables here
        self.base_spread = 4.74  # Starting spread based on analysis
        self.max_position = 20  # Max position limit for AMETHYSTS

    def calculate_spread(self, current_mid_price):
        # Dynamically adjust the spread based on market conditions
        # This is a simplistic approach; you could make this more sophisticated
        spread_adjustment = (
            current_mid_price * 0.0005
        )  # Adjust spread by a factor of the mid price
        return max(self.base_spread, spread_adjustment)

    def run(self, state: TradingState):
        result = {}
        product = "AMETHYSTS"

        if product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Calculate mid price if both bid and ask are available
            if order_depth.buy_orders and order_depth.sell_orders:
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                mid_price = (best_bid + best_ask) / 2

                # Calculate dynamic spread
                spread = self.calculate_spread(mid_price)
                bid_price = mid_price - spread / 2
                ask_price = mid_price + spread / 2

                # Calculate dynamic order size based on current position
                current_position = state.position.get(product, 0)
                order_size = min(
                    5, self.max_position - abs(current_position)
                )  # Keep order size within limits

                # Place buy order if below position limit
                if current_position + order_size <= self.max_position:
                    orders.append(Order(product, bid_price, order_size))

                # Place sell order if below position limit
                if current_position - order_size >= -self.max_position:
                    orders.append(Order(product, ask_price, -order_size))

            result[product] = orders

        # Placeholder for trader data and conversions, adjust as needed
        traderData = "Updated state or info you want to track"
        conversions = 0  # No conversions for this strategy
        return result, conversions, traderData


# Remember to replace 'datamodel' with the actual module name if it's different.
