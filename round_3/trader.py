from datamodel import OrderDepth, TradingState, Order
from typing import List
import json
from datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    ProsperityEncoder,
    Symbol,
    Trade,
    TradingState,
)
from typing import Any
import numpy as np
import math


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 100000

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(
        self,
        state: TradingState,
        orders: dict[Symbol, list[Order]],
        conversions: int,
        trader_data: str,
    ) -> None:
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
                    self.compress_state(
                        state, self.truncate(state.traderData, max_item_length)
                    ),
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
            compressed.append(
                [listing["symbol"], listing["product"], listing["denomination"]]
            )

        return compressed

    def compress_order_depths(
        self, order_depths: dict[Symbol, OrderDepth]
    ) -> dict[Symbol, list[Any]]:
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
    CHOCOLATE: 232,
    STRAWBERRIES: 348,
    ROSES: 58,
    GIFT_BASKET: 58,
}

GIFT_BASKET_CONTENTS = {
    CHOCOLATE: 4,
    STRAWBERRIES: 6,
    ROSES: 1,
}

PRICE_OFFSET = 100
PERCENT_THRESHOLD = 0.14
ORDER_SLOWING_FACTOR = 2

logger = Logger()


class Trader:
    def computeMidPrice(self, state: TradingState, product: str, use_best: bool = True):
        i = -1
        if use_best:
            i = 0
        return int(
            np.round(
                (
                    list(state.order_depths[product].buy_orders.items())[i][0]
                    + list(state.order_depths[product].sell_orders.items())[i][0]
                )
                / 2
            )
        )

    def computeGiftBasketPremium(self, state: TradingState, use_best=True):
        giftBasketMidPrice = self.computeMidPrice(state, GIFT_BASKET, use_best)
        chocolateMidPrice = self.computeMidPrice(state, CHOCOLATE, use_best)
        strawberryMidPrice = self.computeMidPrice(state, STRAWBERRIES, use_best)
        roseMidPrice = self.computeMidPrice(state, ROSES, use_best)
        return giftBasketMidPrice - (
            chocolateMidPrice * GIFT_BASKET_CONTENTS[CHOCOLATE]
            + strawberryMidPrice * GIFT_BASKET_CONTENTS[STRAWBERRIES]
            + roseMidPrice * GIFT_BASKET_CONTENTS[ROSES]
        )

    def maxGiftBasketsToBuy(self, state: TradingState):
        gift_baskets_for_sale = sum(
            -ask_amount
            for _, ask_amount in list(
                state.order_depths[GIFT_BASKET].sell_orders.items()
            )
        )

        strawberris_for_buy = sum(
            bid_amount
            for _, bid_amount in list(
                state.order_depths[STRAWBERRIES].buy_orders.items()
            )
        )
        chocolates_for_buy = sum(
            bid_amount
            for _, bid_amount in list(state.order_depths[CHOCOLATE].buy_orders.items())
        )
        roses_for_buy = sum(
            bid_amount
            for _, bid_amount in list(state.order_depths[ROSES].buy_orders.items())
        )

        return math.floor(
            min(
                gift_baskets_for_sale,
                strawberris_for_buy / GIFT_BASKET_CONTENTS[STRAWBERRIES],
                chocolates_for_buy / GIFT_BASKET_CONTENTS[CHOCOLATE],
                roses_for_buy / GIFT_BASKET_CONTENTS[ROSES],
            )
        )

    def maxGiftBasketsToSell(self, state: TradingState):
        gift_baskets_for_buy = sum(
            bid_amount
            for _, bid_amount in list(
                state.order_depths[GIFT_BASKET].buy_orders.items()
            )
        )

        strawberris_for_sale = sum(
            -ask_amount
            for _, ask_amount in list(
                state.order_depths[STRAWBERRIES].sell_orders.items()
            )
        )
        chocolates_for_sale = sum(
            -ask_amount
            for _, ask_amount in list(state.order_depths[CHOCOLATE].sell_orders.items())
        )
        roses_for_sale = sum(
            -ask_amount
            for _, ask_amount in list(state.order_depths[ROSES].sell_orders.items())
        )

        return math.floor(
            min(
                gift_baskets_for_buy,
                strawberris_for_sale / GIFT_BASKET_CONTENTS[STRAWBERRIES],
                chocolates_for_sale / GIFT_BASKET_CONTENTS[CHOCOLATE],
                roses_for_sale / GIFT_BASKET_CONTENTS[ROSES],
            )
        )

    def createOrdersForGiftBasketTrade(
        self, state: TradingState, num_gift_baskets: int
    ):
        if num_gift_baskets == 0:
            return {}

        if num_gift_baskets > 0:
            # Buying Gift Baskets
            max_gift_baskets_to_buy = self.maxGiftBasketsToBuy(state)
            quantity = min(num_gift_baskets, max_gift_baskets_to_buy)
            quantity = max(1, int(quantity / ORDER_SLOWING_FACTOR))
            logger.print(
                f"Buying {num_gift_baskets} gift baskets: qty={quantity}, price={self.computeMidPrice(state, GIFT_BASKET) + PRICE_OFFSET}"
            )

            return {
                GIFT_BASKET: Order(
                    GIFT_BASKET,
                    self.computeMidPrice(state, GIFT_BASKET) + PRICE_OFFSET,
                    quantity,
                ),
                STRAWBERRIES: Order(
                    STRAWBERRIES,
                    self.computeMidPrice(state, STRAWBERRIES) - PRICE_OFFSET,
                    -GIFT_BASKET_CONTENTS[STRAWBERRIES] * quantity,
                ),
                CHOCOLATE: Order(
                    CHOCOLATE,
                    self.computeMidPrice(state, CHOCOLATE) - PRICE_OFFSET,
                    -GIFT_BASKET_CONTENTS[CHOCOLATE] * quantity,
                ),
                ROSES: Order(
                    ROSES,
                    self.computeMidPrice(state, ROSES) - PRICE_OFFSET,
                    -GIFT_BASKET_CONTENTS[ROSES] * quantity,
                ),
            }

        # Selling Gift Baskets
        max_gift_baskets_to_sell = self.maxGiftBasketsToSell(state)
        quantity = min(-num_gift_baskets, max_gift_baskets_to_sell)
        quantity = max(1, int(quantity / ORDER_SLOWING_FACTOR))
        logger.print(
            f"Selling {num_gift_baskets} gift baskets: qty={quantity}, price={self.computeMidPrice(state, GIFT_BASKET) - PRICE_OFFSET}"
        )
        return {
            GIFT_BASKET: Order(
                GIFT_BASKET,
                self.computeMidPrice(state, GIFT_BASKET) - PRICE_OFFSET,
                -quantity,
            ),
            STRAWBERRIES: Order(
                STRAWBERRIES,
                self.computeMidPrice(state, STRAWBERRIES) + PRICE_OFFSET,
                GIFT_BASKET_CONTENTS[STRAWBERRIES] * quantity,
            ),
            CHOCOLATE: Order(
                CHOCOLATE,
                self.computeMidPrice(state, CHOCOLATE) + PRICE_OFFSET,
                GIFT_BASKET_CONTENTS[CHOCOLATE] * quantity,
            ),
            ROSES: Order(
                ROSES,
                self.computeMidPrice(state, ROSES) + PRICE_OFFSET,
                GIFT_BASKET_CONTENTS[ROSES] * quantity,
            ),
        }

    def run(self, state: TradingState):
        result = {}

        prev_trader_data = json.loads(state.traderData) if state.traderData else {}
        prev_avg_gift_basket_premium = prev_trader_data.get(
            "avg_gift_basket_premium", 379
        )
        prev_count = prev_trader_data.get("count", 1000)

        gift_basket_pos = state.position.get(GIFT_BASKET, 0)
        real_premium = self.computeGiftBasketPremium(state)

        orders = {}
        if prev_avg_gift_basket_premium is not None:
            pct_change = (
                real_premium - prev_avg_gift_basket_premium
            ) / prev_avg_gift_basket_premium
            logger.print(
                f"Real premium: {real_premium}, avg premium: {prev_avg_gift_basket_premium}, pct_change: {pct_change}"
            )

            if pct_change > PERCENT_THRESHOLD:
                # Sell as many as possible
                logger.print("Sell as many as possible")
                orders = self.createOrdersForGiftBasketTrade(
                    state, -POSITION_LIMITS[GIFT_BASKET] - gift_basket_pos
                )
            elif pct_change < -PERCENT_THRESHOLD:
                # Buy as many as possible
                logger.print("Buy as many as possible")
                orders = self.createOrdersForGiftBasketTrade(
                    state, POSITION_LIMITS[GIFT_BASKET] - gift_basket_pos
                )

        if orders.get(GIFT_BASKET):
            result[GIFT_BASKET] = [orders[GIFT_BASKET]]
        if orders.get(STRAWBERRIES):
            result[STRAWBERRIES] = [orders[STRAWBERRIES]]
        if orders.get(CHOCOLATE):
            result[CHOCOLATE] = [orders[CHOCOLATE]]
        if orders.get(ROSES):
            result[ROSES] = [orders[ROSES]]

        new_count = prev_count + 1
        new_avg_gift_basket_premium = (
            prev_avg_gift_basket_premium
            if prev_avg_gift_basket_premium is not None
            else 0
        )
        new_avg_gift_basket_premium = (
            (new_avg_gift_basket_premium * prev_count) + real_premium
        ) / new_count

        new_trader_data = {
            "avg_gift_basket_premium": new_avg_gift_basket_premium,
            "count": new_count,
            "real_premium": real_premium,
        }
        trader_data = json.dumps(
            new_trader_data
        )  # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.
        conversions = 0

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
