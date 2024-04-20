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
PERCENT_THRESHOLD = 0.06
ORDER_SLOWING_FACTOR = 3

logger = Logger()


class Trader:

    # def buyIndividualItem(self, product: str, asks: List[tuple]):
    #     amount_to_buy = 0
    #     highest_ask = 0
    #     total_price = 0
    #     while amount_to_buy < GIFT_BASKET_CONTENTS[product]:
    #         if len(asks) <= 0:
    #             return (False, 0, 0, 0)

    #         remaining_amount_to_buy = GIFT_BASKET_CONTENTS[product] - amount_to_buy
    #         ask, ask_amount = asks[0]
    #         ask_amount = -ask_amount

    #         amount_to_buy_in_lot = min(ask_amount, remaining_amount_to_buy)

    #         total_price += amount_to_buy_in_lot * ask
    #         amount_to_buy += amount_to_buy_in_lot
    #         highest_ask = ask

    #         if ask_amount - amount_to_buy_in_lot == 0:
    #             asks.pop(0)
    #         else:
    #             asks[0] = (ask, -ask_amount + amount_to_buy_in_lot)

    #     if amount_to_buy < GIFT_BASKET_CONTENTS[product]:
    #         return (False, 0, 0, 0)

    #     return (True, amount_to_buy, highest_ask, total_price)

    # def sellIndividualItem(self, product: str, bids: List[tuple]):
    #     amount_to_sell = 0
    #     highest_bid = 0
    #     total_price = 0
    #     while amount_to_sell < GIFT_BASKET_CONTENTS[product]:
    #         if len(bids) <= 0:
    #             return (False, 0, 0, 0)

    #         remaining_amount_to_buy = GIFT_BASKET_CONTENTS[product] - amount_to_sell
    #         bid, bid_amount = bids[0]

    #         amount_to_buy_in_lot = min(bid_amount, remaining_amount_to_buy)

    #         total_price += amount_to_buy_in_lot * bid
    #         amount_to_sell += amount_to_buy_in_lot
    #         highest_bid = bid

    #         if bid_amount - amount_to_buy_in_lot == 0:
    #             bids.pop(0)
    #         else:
    #             bids[0] = (bid, bid_amount - amount_to_buy_in_lot)

    #     if amount_to_sell < GIFT_BASKET_CONTENTS[product]:
    #         return (False, 0, 0, 0)

    #     return (True, amount_to_sell, highest_bid, total_price)

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
                # STRAWBERRIES: Order(
                #     STRAWBERRIES,
                #     self.computeMidPrice(state, STRAWBERRIES) - PRICE_OFFSET,
                #     -GIFT_BASKET_CONTENTS[STRAWBERRIES] * quantity,
                # ),
                # CHOCOLATE: Order(
                #     CHOCOLATE,
                #     self.computeMidPrice(state, CHOCOLATE) - PRICE_OFFSET,
                #     -GIFT_BASKET_CONTENTS[CHOCOLATE] * quantity,
                # ),
                # ROSES: Order(
                #     ROSES,
                #     self.computeMidPrice(state, ROSES) - PRICE_OFFSET,
                #     -GIFT_BASKET_CONTENTS[ROSES] * quantity,
                # ),
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
            # STRAWBERRIES: Order(
            #     STRAWBERRIES,
            #     self.computeMidPrice(state, STRAWBERRIES) + PRICE_OFFSET,
            #     GIFT_BASKET_CONTENTS[STRAWBERRIES] * quantity,
            # ),
            # CHOCOLATE: Order(
            #     CHOCOLATE,
            #     self.computeMidPrice(state, CHOCOLATE) + PRICE_OFFSET,
            #     GIFT_BASKET_CONTENTS[CHOCOLATE] * quantity,
            # ),
            # ROSES: Order(
            #     ROSES,
            #     self.computeMidPrice(state, ROSES) + PRICE_OFFSET,
            #     GIFT_BASKET_CONTENTS[ROSES] * quantity,
            # ),
        }

    def run(self, state: TradingState):
        result = {}

        prev_trader_data = json.loads(state.traderData) if state.traderData else {}
        prev_avg_gift_basket_premium = prev_trader_data.get(
            "avg_gift_basket_premium"
        )  # 379
        prev_count = prev_trader_data.get("count", 0)

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


###############################################################################
# OLD CODE
###############################################################################
# def run(self, state: TradingState):
#     result = {}

#     prev_trader_data = json.loads(state.traderData) if state.traderData else {}
#     prev_avg_gift_basket_premium = prev_trader_data.get(
#         "avg_gift_basket_premium"
#     )  # 379
#     prev_count = prev_trader_data.get("count", 0)

#     gift_basket_pos = state.position.get(GIFT_BASKET, 0)
#     real_premium = self.computeGiftBasketPremium(state)

#     orders = {}
#     if prev_avg_gift_basket_premium is not None and prev_count > 100:
#         pct_change = (
#             real_premium - prev_avg_gift_basket_premium
#         ) / prev_avg_gift_basket_premium
#         level = -pct_change / PERCENT_THRESHOLD
#         desired_position = min(
#             max(
#                 -POSITION_LIMITS[GIFT_BASKET],
#                 int(np.round(POSITION_LIMITS[GIFT_BASKET] * level)),
#             ),
#             POSITION_LIMITS[GIFT_BASKET],
#         )
#         logger.print(
#             f"Real premium: {real_premium}, avg premium: {prev_avg_gift_basket_premium}, pct_change: {pct_change}, level: {level}, desired_position: {desired_position}"
#         )

#         # Get to desired position
#         logger.print("Get to desired position")
#         orders = self.createOrdersForGiftBasketTrade(
#             state, desired_position - gift_basket_pos
#         )

#     if orders.get(GIFT_BASKET):
#         result[GIFT_BASKET] = [orders[GIFT_BASKET]]
#     if orders.get(STRAWBERRIES):
#         result[STRAWBERRIES] = [orders[STRAWBERRIES]]
#     if orders.get(CHOCOLATE):
#         result[CHOCOLATE] = [orders[CHOCOLATE]]
#     if orders.get(ROSES):
#         result[ROSES] = [orders[ROSES]]

#     new_count = prev_count + 1
#     new_avg_gift_basket_premium = (
#         prev_avg_gift_basket_premium
#         if prev_avg_gift_basket_premium is not None
#         else 0
#     )
#     new_avg_gift_basket_premium = (
#         (new_avg_gift_basket_premium * prev_count) + real_premium
#     ) / new_count

#     new_trader_data = {
#         "avg_gift_basket_premium": new_avg_gift_basket_premium,
#         "count": new_count,
#         "real_premium": real_premium,
#     }
#     trader_data = json.dumps(
#         new_trader_data
#     )  # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.
#     conversions = 0

#     logger.flush(state, result, conversions, trader_data)
#     return result, conversions, trader_data


# def run(self, state: TradingState):
#     result = {}
#     PERCENT_THRESHOLD = 0.05

#     prev_trader_data = json.loads(state.traderData) if state.traderData else {}
#     prev_avg_gift_basket_premium = prev_trader_data.get(
#         "avg_gift_basket_premium"
#     )  # 379
#     prev_count = prev_trader_data.get("count", 0)

#     use_best = True
#     gift_basket_mid_price = self.computeMidPrice(
#         state, GIFT_BASKET, use_best=use_best
#     )
#     chocolate_mid_price = self.computeMidPrice(state, CHOCOLATE, use_best=use_best)
#     strawberries_mid_price = self.computeMidPrice(
#         state, STRAWBERRIES, use_best=use_best
#     )
#     roses_mid_price = self.computeMidPrice(state, ROSES, use_best=use_best)
#     real_premium = self.computeGiftBasketPremium(state, use_best=use_best)

#     if real_premium > prev_avg_gift_basket_premium:
#         # Sell baskets and buy strawberries, chocolate, and roses
#         gift_basket_bids = list(state.order_depths[GIFT_BASKET].buy_orders.items())
#         strawberry_asks = list(state.order_depths[STRAWBERRIES].sell_orders.items())
#         chocolate_asks = list(state.order_depths[CHOCOLATE].sell_orders.items())
#         rose_asks = list(state.order_depths[ROSES].sell_orders.items())

#         done = False
#         for gift_basket_bid, gift_basket_bid_amount in gift_basket_bids:
#             if done:
#                 break

#             for i in range(gift_basket_bid_amount):
#                 if (
#                     (
#                         state.position.get(GIFT_BASKET, 0) + orders[GIFT_BASKET][0]
#                         < -POSITION_LIMITS[GIFT_BASKET] + 1
#                     )
#                     or (
#                         state.position.get(STRAWBERRIES, 0)
#                         + orders[STRAWBERRIES][0]
#                         > POSITION_LIMITS[STRAWBERRIES]
#                         - GIFT_BASKET_CONTENTS[STRAWBERRIES]
#                     )
#                     or (
#                         state.position.get(CHOCOLATE, 0) + orders[CHOCOLATE][0]
#                         > POSITION_LIMITS[CHOCOLATE]
#                         - GIFT_BASKET_CONTENTS[CHOCOLATE]
#                     )
#                     or (
#                         state.position.get(ROSES, 0) + orders[ROSES][0]
#                         > POSITION_LIMITS[ROSES] - GIFT_BASKET_CONTENTS[ROSES]
#                     )
#                 ):
#                     done = True
#                     break

#                 (
#                     can_buy_strawberries,
#                     strawberries_amount_to_buy,
#                     strawberries_highest_ask,
#                     strawberries_total_price,
#                 ) = self.buyIndividualItem(STRAWBERRIES, strawberry_asks)
#                 if not can_buy_strawberries:
#                     done = True
#                     break

#                 (
#                     can_buy_chocolates,
#                     chocolates_amount_to_buy,
#                     chocolates_highest_ask,
#                     chocolates_total_price,
#                 ) = self.buyIndividualItem(CHOCOLATE, chocolate_asks)
#                 if not can_buy_chocolates:
#                     done = True
#                     break

#                 (
#                     can_buy_roses,
#                     roses_amount_to_buy,
#                     roses_highest_ask,
#                     roses_total_price,
#                 ) = self.buyIndividualItem(ROSES, rose_asks)
#                 if not can_buy_roses:
#                     done = True
#                     break

#                 sell_basket_real_premium = gift_basket_bid - (
#                     strawberries_total_price
#                     + chocolates_total_price
#                     + roses_total_price
#                 )

#                 if prev_avg_gift_basket_premium is None:
#                     done = True
#                     break

#                 premium_percent_change = (
#                     sell_basket_real_premium - prev_avg_gift_basket_premium
#                 ) / prev_avg_gift_basket_premium

#                 if premium_percent_change <= 0:
#                     done = True
#                     break

#                 if (
#                     premium_percent_change <= PERCENT_THRESHOLD
#                     and state.position.get(GIFT_BASKET, 0) + orders[GIFT_BASKET][0]
#                     <= 0
#                 ):
#                     done = True
#                     break

#                 orders[GIFT_BASKET] = (orders[GIFT_BASKET][0] - 1, gift_basket_bid)
#                 orders[STRAWBERRIES] = (
#                     orders[STRAWBERRIES][0] + strawberries_amount_to_buy,
#                     strawberries_highest_ask,
#                 )
#                 orders[CHOCOLATE] = (
#                     orders[CHOCOLATE][0] + chocolates_amount_to_buy,
#                     chocolates_highest_ask,
#                 )
#                 orders[ROSES] = (
#                     orders[ROSES][0] + roses_amount_to_buy,
#                     roses_highest_ask,
#                 )

#     else:
#         # Buy baskets and sell strawberries, chocolate, and roses
#         gift_basket_asks = list(state.order_depths[GIFT_BASKET].sell_orders.items())
#         strawberry_bids = list(state.order_depths[STRAWBERRIES].buy_orders.items())
#         chocolate_bids = list(state.order_depths[CHOCOLATE].buy_orders.items())
#         rose_bids = list(state.order_depths[ROSES].buy_orders.items())

#         done = False
#         for gift_basket_ask, gift_basket_ask_amount in gift_basket_asks:
#             if done:
#                 break

#             for i in range(-gift_basket_ask_amount):
#                 if (
#                     (
#                         state.position.get(GIFT_BASKET, 0) + orders[GIFT_BASKET][0]
#                         > POSITION_LIMITS[GIFT_BASKET] - 1
#                     )
#                     or (
#                         state.position.get(STRAWBERRIES, 0)
#                         + orders[STRAWBERRIES][0]
#                         < -POSITION_LIMITS[STRAWBERRIES]
#                         + GIFT_BASKET_CONTENTS[STRAWBERRIES]
#                     )
#                     or (
#                         state.position.get(CHOCOLATE, 0) + orders[CHOCOLATE][0]
#                         < -POSITION_LIMITS[CHOCOLATE]
#                         + GIFT_BASKET_CONTENTS[CHOCOLATE]
#                     )
#                     or (
#                         state.position.get(ROSES, 0) + orders[ROSES][0]
#                         < -POSITION_LIMITS[ROSES] + GIFT_BASKET_CONTENTS[ROSES]
#                     )
#                 ):
#                     done = True
#                     break

#                 (
#                     can_sell_strawberries,
#                     strawberries_amount_to_sell,
#                     strawberries_lowest_bid,
#                     strawberries_total_price,
#                 ) = self.sellIndividualItem(STRAWBERRIES, strawberry_bids)
#                 if not can_sell_strawberries:
#                     done = True
#                     break

#                 (
#                     can_sell_chocolates,
#                     chocolates_amount_to_sell,
#                     chocolates_lowest_bid,
#                     chocolates_total_price,
#                 ) = self.sellIndividualItem(CHOCOLATE, chocolate_bids)
#                 if not can_sell_chocolates:
#                     done = True
#                     break

#                 (
#                     can_sell_roses,
#                     roses_amount_to_sell,
#                     roses_lowest_bid,
#                     roses_total_price,
#                 ) = self.sellIndividualItem(ROSES, rose_bids)
#                 if not can_sell_roses:
#                     done = True
#                     break

#                 buy_basket_real_premium = gift_basket_ask - (
#                     strawberries_total_price
#                     + chocolates_total_price
#                     + roses_total_price
#                 )

#                 if prev_avg_gift_basket_premium is None:
#                     done = True
#                     break

#                 premium_percent_change = (
#                     buy_basket_real_premium - prev_avg_gift_basket_premium
#                 ) / prev_avg_gift_basket_premium

#                 if premium_percent_change >= 0:
#                     done = True
#                     break

#                 if (
#                     premium_percent_change >= -PERCENT_THRESHOLD
#                     and state.position.get(GIFT_BASKET, 0) + orders[GIFT_BASKET][0]
#                     >= 0
#                 ):
#                     done = True
#                     break

#                 orders[GIFT_BASKET] = (orders[GIFT_BASKET][0] + 1, gift_basket_ask)
#                 orders[STRAWBERRIES] = (
#                     orders[STRAWBERRIES][0] - strawberries_amount_to_sell,
#                     strawberries_lowest_bid,
#                 )
#                 orders[CHOCOLATE] = (
#                     orders[CHOCOLATE][0] - chocolates_amount_to_sell,
#                     chocolates_lowest_bid,
#                 )
#                 orders[ROSES] = (
#                     orders[ROSES][0] - roses_amount_to_sell,
#                     roses_lowest_bid,
#                 )

#     if orders[GIFT_BASKET][0] != 0:
#         result[GIFT_BASKET] = [
#             Order(GIFT_BASKET, orders[GIFT_BASKET][1], orders[GIFT_BASKET][0])
#         ]
#         result[STRAWBERRIES] = [
#             Order(STRAWBERRIES, orders[STRAWBERRIES][1], orders[STRAWBERRIES][0])
#         ]
#         result[CHOCOLATE] = [
#             Order(CHOCOLATE, orders[CHOCOLATE][1], orders[CHOCOLATE][0])
#         ]
#         result[ROSES] = [Order(ROSES, orders[ROSES][1], orders[ROSES][0])]

#     new_count = prev_count + 1
#     new_avg_gift_basket_premium = (
#         prev_avg_gift_basket_premium
#         if prev_avg_gift_basket_premium is not None
#         else 0
#     )
#     new_avg_gift_basket_premium = (
#         (new_avg_gift_basket_premium * prev_count) + real_premium
#     ) / new_count

#     new_trader_data = {
#         "avg_gift_basket_premium": new_avg_gift_basket_premium,
#         "count": new_count,
#         "real_premium": real_premium,
#     }
#     trader_data = json.dumps(
#         new_trader_data
#     )  # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.
#     conversions = 0

#     logger.flush(state, result, conversions, trader_data)
#     return result, conversions, trader_data
