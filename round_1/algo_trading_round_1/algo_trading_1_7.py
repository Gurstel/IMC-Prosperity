from datamodel import OrderDepth, TradingState, Order
from typing import List
import numpy as np


class Trader:

    POSITION_LIMIT = 20
    position = 0
    volume_traded = 0
    cpnl = 0  # Cumulative PnL

    def compute_orders_amethysts(self, product, order_depth):
        orders = []

        # Simplified market analysis for demonstration purposes
        sell_orders = sorted(order_depth.sell_orders.items())
        buy_orders = sorted(order_depth.buy_orders.items(), reverse=True)

        # Strategy adjustment based on market conditions
        if self.position < 0:  # If currently holding a short position, look to buy
            for price, volume in buy_orders:
                if self.position + volume <= self.POSITION_LIMIT:
                    orders.append(Order(product, price, volume))
                    self.position += volume
                else:
                    break
        elif self.position > 0:  # If holding a long position, look to sell
            for price, volume in sell_orders:
                volume = -volume  # Selling reduces position
                if self.position + volume >= -self.POSITION_LIMIT:
                    orders.append(Order(product, price, -volume))
                    self.position += volume
                else:
                    break
        else:  # Neutral position, trade based on market imbalance
            if len(buy_orders) > len(sell_orders):  # Market appears bullish
                for price, volume in buy_orders[:1]:  # Limited to 1 to manage risk
                    if volume <= self.POSITION_LIMIT:
                        orders.append(Order(product, price, volume))
                        self.position += volume
            else:  # Market appears bearish
                for price, volume in sell_orders[:1]:  # Limited to 1 to manage risk
                    orders.append(Order(product, price, -volume))
                    self.position -= volume

        return orders

    def run(self, state: TradingState):
        result = {"AMETHYSTS": []}
        self.position = state.position.get("AMETHYSTS", 0)

        order_depth: OrderDepth = state.order_depths["AMETHYSTS"]
        orders = self.compute_orders_amethysts("AMETHYSTS", order_depth)
        result["AMETHYSTS"] = orders

        for trade in state.own_trades.get("AMETHYSTS", []):
            self.volume_traded += abs(trade.quantity)
            if trade.buyer == "SUBMISSION":
                self.cpnl -= trade.quantity * trade.price
            else:
                self.cpnl += trade.quantity * trade.price

        print(
            f"AMETHYSTS Position: {self.position}, Volume Traded: {self.volume_traded}, Cumulative PnL: {self.cpnl}"
        )
        conversions = 0
        traderData = "SAMPLE"
        return result, conversions, traderData
