from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import math


class Trader:
    def __init__(self):
        self.base_spread = {
            "AMETHYSTS": 4.74,  # Base spread for AMETHYSTS
            "STARFRUIT": 5.00,  # Initial spread for STARFRUIT, could be adjusted dynamically
        }
        self.max_position = 20
        self.rolling_prices: Dict[str, List[float]] = {"STARFRUIT": []}  # Store rolling prices for STARFRUIT
        self.max_historical_prices = 20  # Max historical prices to keep for trend analysis
        self.safety_margin = 0.02  # Safety margin for mean reversion strategy

    def calculate_spread(self, product, current_mid_price):
        # Adjust spread based on the product type
        spread_adjustment = current_mid_price * (0.0005 if product == "AMETHYSTS" else 0.001)
        return max(self.base_spread[product], spread_adjustment)

    def maximize_order_size(self, current_position):
        # Maximize order size to swing positions for AMETHYSTS
        return self.max_position - abs(current_position) if current_position >= 0 else -self.max_position - current_position

    def calculate_volatility(self, prices):
        # Simplistic volatility calculation for STARFRUIT
        if len(prices) < 2:
            return 0
        avg_price = sum(prices) / len(prices)
        variance = sum((p - avg_price) ** 2 for p in prices) / (len(prices) - 1)
        return math.sqrt(variance)

    def calculate_trend(self, prices):
        # Identify trend based on recent price changes
        if len(prices) < 2:
            return 0
        return prices[-1] - prices[-2]

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

                    current_position = state.position.get(product, 0)

                    if product == "AMETHYSTS":
                        spread = self.calculate_spread(product, mid_price)
                        bid_price = math.floor(mid_price - spread / 2)
                        ask_price = math.ceil(mid_price + spread / 2)
                        order_size = self.maximize_order_size(current_position)
                        if order_size > 0:
                            orders.append(Order(product, bid_price, -order_size))
                        else:
                            orders.append(Order(product, ask_price, order_size))

                    elif product == "STARFRUIT":
                        self.rolling_prices[product].append(mid_price)
                        if len(self.rolling_prices[product]) > self.max_historical_prices:
                            self.rolling_prices[product].pop(0)
                        volatility = self.calculate_volatility(self.rolling_prices[product])
                        trend = self.calculate_trend(self.rolling_prices[product])

                        if abs(trend) > volatility * self.safety_margin:
                            if trend > 0 and current_position < self.max_position:
                                orders.append(Order(product, math.ceil(mid_price), -self.max_position))
                            elif trend < 0 and current_position > -self.max_position:
                                orders.append(Order(product, math.floor(mid_price), self.max_position))

                result[product] = orders

        traderData = "Adaptive strategy with dynamic data"
        conversions = 0
        return result, conversions, traderData
