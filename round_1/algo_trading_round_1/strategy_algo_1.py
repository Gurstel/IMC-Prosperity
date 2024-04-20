from typing import Dict, List, Tuple
from datamodel import Order, TradingState, OrderDepth
import numpy as np

AMETHYSTS_PRICE = 10000


class Trader:

    def __init__(self):
        self.products = {"AMETHYSTS": Amethysts(), "STARFRUIT": Starfruit()}
        # Amethyst gets 800 seashells
        # Starfruit gets 817 seashells

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """

        # Initialize the method output dict as an empty dict
        result = {}

        for product in state.order_depths.keys():
            if product in self.products.keys():
                orders: list[Order] = []

                self.products[product].reset_from_state(state)
                self.products[product].trade(trading_state=state, orders=orders)
                result[product] = orders

        conversions = 0
        traderData = "SAMPLE"
        return result, conversions, traderData


class Strategy:
    def __init__(self, name: str, max_position: int):
        self.name: str = name
        self.cached_prices: list = []
        self.cached_means: list = []
        self.max_pos: int = max_position
        self.trade_count: int = 1

        self.prod_position: int = 0
        self.new_buy_orders: int = 0
        self.new_sell_orders: int = 0
        self.order_depth: OrderDepth = OrderDepth()

    def reset_from_state(self, state: TradingState):
        self.prod_position = (
            state.position[self.name] if self.name in state.position.keys() else 0
        )
        self.order_depth: OrderDepth = state.order_depths[self.name]

        self.new_buy_orders = 0
        self.new_sell_orders = 0

    def sell_product(self, best_bids, i, order_depth, orders):
        # Sell product at best bid
        best_bid_volume = order_depth.buy_orders[best_bids[i]]
        if self.prod_position - best_bid_volume >= -self.max_pos:
            orders.append(Order(self.name, best_bids[i], -best_bid_volume))
            self.prod_position += -best_bid_volume
            self.new_sell_orders += best_bid_volume

        else:
            # Sell as much as we can without exceeding the self.max_pos[product]
            vol = self.prod_position + self.max_pos
            orders.append(Order(self.name, best_bids[i], -vol))
            self.prod_position += -vol
            self.new_sell_orders += vol

    def buy_product(self, best_asks, i, order_depth, orders):
        # Buy product at best ask
        best_ask_volume = order_depth.sell_orders[best_asks[i]]
        if self.prod_position - best_ask_volume <= self.max_pos:
            orders.append(Order(self.name, best_asks[i], -best_ask_volume))
            self.prod_position += -best_ask_volume
            self.new_buy_orders += -best_ask_volume
        else:
            # Buy as much as we can without exceeding the self.max_pos[product]
            vol = self.max_pos - self.prod_position
            orders.append(Order(self.name, best_asks[i], vol))
            self.prod_position += vol
            self.new_buy_orders += vol


class FixedStrategy(Strategy):
    def __init__(self, name: str, max_pos: int):
        super().__init__(name, max_pos)
        self.amethysts_price = 10000
        self.amethysts_diff = 3

    def trade(self, trading_state: TradingState, orders: list):
        order_depth: OrderDepth = trading_state.order_depths[self.name]
        # Check if there are any SELL orders
        if len(order_depth.sell_orders) > 0:
            #
            # self.cache_prices(order_depth)
            # Sort all the available sell orders by their price
            best_asks = sorted(order_depth.sell_orders.keys())

            # Check if the lowest ask (sell order) is lower than the above defined fair value
            i = 0
            while i < self.trade_count and best_asks[i] < self.amethysts_price:
                # Fill ith ask order if it's below the acceptable
                if self.prod_position == self.max_pos:
                    break
                self.buy_product(best_asks, i, order_depth, orders)
                i += 1
        if len(order_depth.buy_orders) != 0:
            best_bids = sorted(order_depth.buy_orders.keys(), reverse=True)

            i = 0
            while i < self.trade_count and best_bids[i] > self.amethysts_price:
                if self.prod_position == -self.max_pos:
                    break
                self.sell_product(best_bids, i, order_depth, orders)
                i += 1


class CrossStrategy(Strategy):
    def __init__(self, name: str, min_req_price_difference: int, max_position: int):
        super().__init__(name, max_position)
        self.strategy_start_day = 2

        self.old_asks = []
        self.old_bids = []
        self.min_req_price_difference = min_req_price_difference

    def trade(self, trading_state: TradingState, orders: list):
        order_depth: OrderDepth = trading_state.order_depths[self.name]
        self.cache_prices(order_depth)
        if (
            len(self.old_asks) < self.strategy_start_day
            or len(self.old_bids) < self.strategy_start_day
        ):
            return

        avg_bid, avg_ask = self.calculate_prices(self.strategy_start_day)

        if len(order_depth.sell_orders) != 0:
            best_asks = sorted(order_depth.sell_orders.keys())

            i = 0
            while (
                i < self.trade_count
                and len(best_asks) > i
                and best_asks[i] - avg_bid <= self.min_req_price_difference
            ):
                if self.prod_position == self.max_pos:
                    break
                self.buy_product(best_asks, i, order_depth, orders)
                i += 1

        if len(order_depth.buy_orders) != 0:
            best_bids = sorted(order_depth.buy_orders.keys(), reverse=True)

            i = 0
            while (
                i < self.trade_count
                and len(best_bids) > i
                and avg_ask - best_bids[i] <= self.min_req_price_difference
            ):
                if self.prod_position == -self.max_pos:
                    break
                self.sell_product(best_bids, i, order_depth, orders)

                i += 1

    def calculate_prices(self, days: int) -> Tuple[int, int]:
        # Calculate the average bid and ask price for the last days

        relevant_bids = []
        for bids in self.old_bids[-days:]:
            relevant_bids.extend([(value, bids[value]) for value in bids])
        relevant_asks = []
        for asks in self.old_asks[-days:]:
            relevant_asks.extend([(value, asks[value]) for value in asks])

        avg_bid = np.average(
            [x[0] for x in relevant_bids], weights=[x[1] for x in relevant_bids]
        )
        avg_ask = np.average(
            [x[0] for x in relevant_asks], weights=[x[1] for x in relevant_asks]
        )

        return avg_bid, avg_ask

    def cache_prices(self, order_depth: OrderDepth):
        sell_orders = order_depth.sell_orders
        buy_orders = order_depth.buy_orders

        self.old_asks.append(sell_orders)
        self.old_bids.append(buy_orders)


class Amethysts(FixedStrategy):
    def __init__(self):
        super().__init__("AMETHYSTS", max_pos=20)


class Starfruit(CrossStrategy):
    def __init__(self):
        super().__init__("STARFRUIT", min_req_price_difference=3, max_position=20)
