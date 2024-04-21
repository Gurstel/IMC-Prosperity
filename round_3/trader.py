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


CHOCOLATE = "CHOCOLATE"
STRAWBERRIES = "STRAWBERRIES"
ROSES = "ROSES"
GIFT_BASKET = "GIFT_BASKET"

POSITION_LIMITS = {
    CHOCOLATE: 250,
    STRAWBERRIES: 350,
    ROSES: 60,
    GIFT_BASKET: 60,
}

GIFT_BASKET_CONTENTS = {
    CHOCOLATE: 4,
    STRAWBERRIES: 6,
    ROSES: 1,
}

logger = Logger()


class Trader:

    def buyIndividualItem(self, product: str, asks: List[tuple]):
        amount_to_buy = 0
        highest_ask = 0
        total_price = 0
        while amount_to_buy < GIFT_BASKET_CONTENTS[product]:
            if len(asks) <= 0:
                return (False, 0, 0, 0)

            remaining_amount_to_buy = GIFT_BASKET_CONTENTS[product] - amount_to_buy
            ask, ask_amount = asks[0]
            ask_amount = -ask_amount

            amount_to_buy_in_lot = min(ask_amount, remaining_amount_to_buy)

            total_price += amount_to_buy_in_lot * ask
            amount_to_buy += amount_to_buy_in_lot
            highest_ask = ask

            if ask_amount - amount_to_buy_in_lot == 0:
                asks.pop(0)
            else:
                asks[0] = (ask, -ask_amount + amount_to_buy_in_lot)

        if amount_to_buy < GIFT_BASKET_CONTENTS[product]:
            return (False, 0, 0, 0)

        return (True, amount_to_buy, highest_ask, total_price)

    def sellIndividualItem(self, product: str, bids: List[tuple]):
        amount_to_sell = 0
        highest_bid = 0
        total_price = 0
        while amount_to_sell < GIFT_BASKET_CONTENTS[product]:
            if len(bids) <= 0:
                return (False, 0, 0, 0)

            remaining_amount_to_buy = GIFT_BASKET_CONTENTS[product] - amount_to_sell
            bid, bid_amount = bids[0]

            amount_to_buy_in_lot = min(bid_amount, remaining_amount_to_buy)

            total_price += amount_to_buy_in_lot * bid
            amount_to_sell += amount_to_buy_in_lot
            highest_bid = bid

            if bid_amount - amount_to_buy_in_lot == 0:
                bids.pop(0)
            else:
                bids[0] = (bid, bid_amount - amount_to_buy_in_lot)

        if amount_to_sell < GIFT_BASKET_CONTENTS[product]:
            return (False, 0, 0, 0)

        return (True, amount_to_sell, highest_bid, total_price)

    def run(self, state: TradingState):
        avg_gift_basket_premium = 379
        percent_threshold = 0.16

        result = {}

        # Sell baskets and buy strawberries, chocolate, and roses
        gift_basket_bids = list(state.order_depths[GIFT_BASKET].buy_orders.items())
        strawberry_asks = list(state.order_depths[STRAWBERRIES].sell_orders.items())
        chocolate_asks = list(state.order_depths[CHOCOLATE].sell_orders.items())
        rose_asks = list(state.order_depths[ROSES].sell_orders.items())

        done = False
        for gift_basket_bid, gift_basket_bid_amount in gift_basket_bids:
            if done:
                break

            for i in range(gift_basket_bid_amount):
                if (
                    (GIFT_BASKET in state.position and state.position[GIFT_BASKET] < -POSITION_LIMITS[GIFT_BASKET] + 1)
                    and (STRAWBERRIES in state.position and state.position[STRAWBERRIES] > POSITION_LIMITS[STRAWBERRIES] - GIFT_BASKET_CONTENTS[STRAWBERRIES])
                    and (CHOCOLATE in state.position and state.position[CHOCOLATE] > POSITION_LIMITS[CHOCOLATE] - GIFT_BASKET_CONTENTS[CHOCOLATE])
                    and (ROSES in state.position and state.position[ROSES] > POSITION_LIMITS[ROSES] - GIFT_BASKET_CONTENTS[ROSES])
                ):
                    done = True
                    break

                (
                    can_buy_strawberries,
                    strawberries_amount_to_buy,
                    strawberries_highest_ask,
                    strawberries_total_price,
                ) = self.buyIndividualItem(STRAWBERRIES, strawberry_asks)
                if not can_buy_strawberries:
                    done = True
                    break

                (
                    can_buy_chocolates,
                    chocolates_amount_to_buy,
                    chocolates_highest_ask,
                    chocolates_total_price,
                ) = self.buyIndividualItem(CHOCOLATE, chocolate_asks)
                if not can_buy_chocolates:
                    done = True
                    break

                (
                    can_buy_roses,
                    roses_amount_to_buy,
                    roses_highest_ask,
                    roses_total_price,
                ) = self.buyIndividualItem(ROSES, rose_asks)
                if not can_buy_roses:
                    done = True
                    break

                # print("should sell basket?")
                # print(f"gift_basket_bid: {gift_basket_bid}")
                # print(
                #     f"individual_total_price: {strawberries_total_price + chocolates_total_price + roses_total_price}"
                # )
                # print(
                #     f"real premium: {gift_basket_bid - (strawberries_total_price + chocolates_total_price + roses_total_price)}"
                # )
                # print(f"avg premium: {avg_gift_basket_premium}")
                # print("\n\n")
                real_premium = gift_basket_bid - (strawberries_total_price + chocolates_total_price + roses_total_price)
                if (real_premium - avg_gift_basket_premium) / avg_gift_basket_premium <= percent_threshold:
                    done = True
                    break

                print("selling basket")
                print("real premium: ", real_premium)
                print("avg premium: ", avg_gift_basket_premium)
                print("\n\n")

                if GIFT_BASKET not in result:
                    result[GIFT_BASKET] = []
                result[GIFT_BASKET].append(Order(GIFT_BASKET, gift_basket_bid, -1))

                if STRAWBERRIES not in result:
                    result[STRAWBERRIES] = []
                result[STRAWBERRIES].append(
                    Order(
                        STRAWBERRIES,
                        strawberries_highest_ask,
                        strawberries_amount_to_buy,
                    )
                )

                if CHOCOLATE not in result:
                    result[CHOCOLATE] = []
                result[CHOCOLATE].append(Order(CHOCOLATE, chocolates_highest_ask, chocolates_amount_to_buy))

                if ROSES not in result:
                    result[ROSES] = []
                result[ROSES].append(Order(ROSES, roses_highest_ask, roses_amount_to_buy))

        # Buy baskets and sell strawberries, chocolate, and roses
        gift_basket_asks = list(state.order_depths[GIFT_BASKET].sell_orders.items())
        strawberry_bids = list(state.order_depths[STRAWBERRIES].buy_orders.items())
        chocolate_bids = list(state.order_depths[CHOCOLATE].buy_orders.items())
        rose_bids = list(state.order_depths[ROSES].buy_orders.items())

        done = False
        for gift_basket_ask, gift_basket_ask_amount in gift_basket_asks:
            if done:
                break

            for i in range(-gift_basket_ask_amount):
                if (
                    (GIFT_BASKET in state.position and state.position[GIFT_BASKET] > POSITION_LIMITS[GIFT_BASKET] - 1)
                    and (STRAWBERRIES in state.position and state.position[STRAWBERRIES] < -POSITION_LIMITS[STRAWBERRIES] + GIFT_BASKET_CONTENTS[STRAWBERRIES])
                    and (CHOCOLATE in state.position and state.position[CHOCOLATE] < -POSITION_LIMITS[CHOCOLATE] + GIFT_BASKET_CONTENTS[CHOCOLATE])
                    and (ROSES in state.position and state.position[ROSES] < -POSITION_LIMITS[ROSES] + GIFT_BASKET_CONTENTS[ROSES])
                ):
                    done = True
                    break

                (
                    can_sell_strawberries,
                    strawberries_amount_to_sell,
                    strawberries_lowest_bid,
                    strawberries_total_price,
                ) = self.sellIndividualItem(STRAWBERRIES, strawberry_bids)
                if not can_sell_strawberries:
                    done = True
                    break

                (
                    can_sell_chocolates,
                    chocolates_amount_to_sell,
                    chocolates_lowest_bid,
                    chocolates_total_price,
                ) = self.sellIndividualItem(CHOCOLATE, chocolate_bids)
                if not can_sell_chocolates:
                    done = True
                    break

                (
                    can_sell_roses,
                    roses_amount_to_sell,
                    roses_lowest_bid,
                    roses_total_price,
                ) = self.sellIndividualItem(ROSES, rose_bids)
                if not can_sell_roses:
                    done = True
                    break

                # print("should buy basket?")
                # print(f"gift_basket_ask: {gift_basket_ask}")
                # print(
                #     f"individual_total_price: {strawberries_total_price + chocolates_total_price + roses_total_price}"
                # )
                # print(
                #     f"real premium: {gift_basket_ask - (strawberries_total_price + chocolates_total_price + roses_total_price)}"
                # )
                # print(f"avg premium: {avg_gift_basket_premium}")
                # print("\n\n")
                real_premium = gift_basket_ask - (strawberries_total_price + chocolates_total_price + roses_total_price)
                if (real_premium - avg_gift_basket_premium) / avg_gift_basket_premium >= -percent_threshold:
                    done = True
                    break

                print("buying basket")
                print("real premium: ", real_premium)
                print("avg premium: ", avg_gift_basket_premium)
                print("\n\n")
                if GIFT_BASKET not in result:
                    result[GIFT_BASKET] = []
                result[GIFT_BASKET].append(Order(GIFT_BASKET, gift_basket_ask, 1))

                if STRAWBERRIES not in result:
                    result[STRAWBERRIES] = []
                result[STRAWBERRIES].append(
                    Order(
                        STRAWBERRIES,
                        strawberries_lowest_bid,
                        -strawberries_amount_to_sell,
                    )
                )

                if CHOCOLATE not in result:
                    result[CHOCOLATE] = []
                result[CHOCOLATE].append(Order(CHOCOLATE, chocolates_lowest_bid, -chocolates_amount_to_sell))

                if ROSES not in result:
                    result[ROSES] = []
                result[ROSES].append(Order(ROSES, roses_lowest_bid, -roses_amount_to_sell))

        trader_data = "SAMPLE"  # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.
        conversions = 0

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
