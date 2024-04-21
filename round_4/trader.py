# Got us to 593.362 during round 2

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
from math import fabs, sqrt, exp, floor
import numpy as np
from statistics import NormalDist
import sys

A = (3.1611237438705656, 113.864154151050156, 377.485237685302021, 3209.37758913846947, 0.185777706184603153)
B = (23.6012909523441209, 244.024637934444173, 1282.61652607737228, 2844.23683343917062)
C = (0.564188496988670089, 8.88314979438837594, 66.1191906371416295, 298.635138197400131, 881.95222124176909, 1712.04761263407058, 2051.07837782607147, 1230.33935479799725, 2.15311535474403846e-8)
D = (15.7449261107098347, 117.693950891312499, 537.181101862009858, 1621.38957456669019, 3290.79923573345963, 4362.61909014324716, 3439.36767414372164, 1230.33935480374942)
P = (0.305326634961232344, 0.360344899949804439, 0.125781726111229246, 0.0160837851487422766, 6.58749161529837803e-4, 0.0163153871373020978)
Q = (2.56852019228982242, 1.87295284992346047, 0.527905102951428412, 0.0605183413124413191, 0.00233520497626869185)

ZERO = 0.0
HALF = 0.5
ONE = 1.0
TWO = 2.0
FOUR = 4.0
SQRPI = 0.56418958354775628695
THRESH = 0.46875
SIXTEEN = 16.0
XINF = 1.79e308
XNEG = -26.628
XSMALL = 1.11e-16
XBIG = 26.543
XHUGE = 6.71e7
XMAX = 2.53e307

DBL_EPSILON = sys.float_info.epsilon
DBL_MAX = sys.float_info.max
DBL_MIN = sys.float_info.min
ONE_OVER_SQRT_TWO_PI = 0.3989422804014326779399460599343818684758586311649
ONE_OVER_SQRT_TWO = 0.7071067811865475244008443621048490392848359376887


def d_int(x):
    return floor(x) if x > 0 else -floor(-x)


def fix_up_for_negative_argument_erf_etc(jint, result, x):
    if jint == 0:
        result = (HALF - result) + HALF
        if x < ZERO:
            result = -result
    elif jint == 1:
        if x < ZERO:
            result = TWO - result
    else:
        if x < ZERO:
            if x < XNEG:
                result = XINF
            else:
                d__1 = x * SIXTEEN
                ysq = d_int(d__1) / SIXTEEN
                _del = (x - ysq) * (x + ysq)
                y = exp(ysq * ysq) * exp(_del)
                result = y + y - result
    return result


def d1(S, K, t, r, sigma):

    sigma_squared = sigma * sigma
    numerator = np.log(S / float(K)) + (r + sigma_squared / 2.0) * t
    denominator = sigma * np.sqrt(t)

    if not denominator:
        print("")
    return numerator / denominator


def calerf(x, jint):
    y = fabs(x)
    if y <= THRESH:
        ysq = ZERO
        if y > XSMALL:
            ysq = y * y
        xnum = A[4] * ysq
        xden = ysq
        for i__ in range(0, 3):
            xnum = (xnum + A[i__]) * ysq
            xden = (xden + B[i__]) * ysq
        result = x * (xnum + A[3]) / (xden + B[3])
        if jint != 0:
            result = ONE - result
        if jint == 2:
            result *= exp(ysq)

        return result
    elif y <= FOUR:
        xnum = C[8] * y
        xden = y
        for i__ in range(0, 7):
            xnum = (xnum + C[i__]) * y
            xden = (xden + D[i__]) * y
        result = (xnum + C[7]) / (xden + D[7])
        if jint != 2:
            d__1 = y * SIXTEEN
            ysq = d_int(d__1) / SIXTEEN
            _del = (y - ysq) * (y + ysq)
            d__1 = exp(-ysq * ysq) * exp(-_del)
            result *= d__1
    else:
        result = ZERO
        if y >= XBIG:
            if jint != 2 or y >= XMAX:
                return fix_up_for_negative_argument_erf_etc(jint, result, x)
            if y >= XHUGE:
                result = SQRPI / y
                return fix_up_for_negative_argument_erf_etc(jint, result, x)
        ysq = ONE / (y * y)
        xnum = P[5] * ysq
        xden = ysq
        for i__ in range(0, 4):
            xnum = (xnum + P[i__]) * ysq
            xden = (xden + Q[i__]) * ysq
        result = ysq * (xnum + P[4]) / (xden + Q[4])
        result = (SQRPI - result) / y
        if jint != 2:
            d__1 = y * SIXTEEN
            ysq = d_int(d__1) / SIXTEEN
            _del = (y - ysq) * (y + ysq)
            d__1 = exp(-ysq * ysq) * exp(-_del)
            result *= d__1
    return fix_up_for_negative_argument_erf_etc(jint, result, x)


def erfc_cody(x):
    return calerf(x, 1)


def norm_pdf(x):
    return ONE_OVER_SQRT_TWO_PI * exp(-0.5 * x * x)


norm_cdf_asymptotic_expansion_first_threshold = -10.0
norm_cdf_asymptotic_expansion_second_threshold = -1 / sqrt(DBL_EPSILON)


def norm_cdf(z):
    if z <= norm_cdf_asymptotic_expansion_first_threshold:
        sum = 1
        if z >= norm_cdf_asymptotic_expansion_second_threshold:
            zsqr = z * z
            i = 1
            g = 1
            x = 0
            y = 0
            a = DBL_MAX

            lasta = a
            x = (4 * i - 3) / zsqr
            y = x * ((4 * i - 1) / zsqr)
            a = g * (x - y)
            sum -= a
            g *= y
            i += 1
            a = fabs(a)
            while lasta > a >= fabs(sum * DBL_EPSILON):
                lasta = a
                x = (4 * i - 3) / zsqr
                y = x * ((4 * i - 1) / zsqr)
                a = g * (x - y)
                sum -= a
                g *= y
                i += 1
                a = fabs(a)
        return -norm_pdf(z) * sum / z
    return 0.5 * erfc_cody(-z * ONE_OVER_SQRT_TWO)


def delta(flag, S, K, t, r, sigma):

    d_1 = d1(S, K, t, r, sigma)

    if flag == "p":
        return norm_cdf(d_1) - 1.0
    else:
        return norm_cdf(d_1)


def delta_calc(r, S, K, T, sigma, type="c"):
    d1 = (np.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    try:
        if type == "c":
            delta_calc = NormalDist().cdf(d1)
        elif type == "p":
            delta_calc = -NormalDist().cdf(-d1)
        return delta_calc, delta(type, S, K, T, r, sigma)
    except Exception as e:
        print(e)
        print("Please confirm option type, either 'c' for Call or 'p' for Put!")


def compute_coconut_coupon_delta(price):
    return delta_calc(0, price, 10000, 0.984, 0.16)


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


logger = Logger()
COCONUT = "COCONUT"
COUPON = "COCONUT_COUPON"

COCONUT_FMV = 10000
COUPON_FMV = 637.63

COUPON_LOADING = 2

TRADE_PERCENT_THRESHOLD = 0.0

POSITION_LIMITS = {
    COCONUT: 300,
    COUPON: 600,
}


class Trader:
    def __init__(self):
        self.conversions = 0
        self.buys = 0
        self.sells = 0

    def get_best_bid(self, state: TradingState, product: str):
        if not state.order_depths[product].buy_orders:
            return 0, 0

        best_bid = max(state.order_depths[product].buy_orders.keys())
        return best_bid, state.order_depths[product].buy_orders[best_bid]

    def get_best_ask(self, state: TradingState, product: str):
        if not state.order_depths[product].sell_orders:
            return 999999, 0

        best_ask = min(state.order_depths[product].sell_orders.keys())
        return best_ask, state.order_depths[product].sell_orders[best_ask]

    def compute_max_coupon_buy_qty(self, state: TradingState):
        # Max quantity of COUPON that can be bought
        best_coupon_ask, _ = self.get_best_ask(state, COUPON)
        available_coupon_ask_qty = sum(q for a, q in state.order_depths[COUPON].sell_orders.items() if a <= best_coupon_ask + 2)
        return math.floor(
            min(
                [
                    -available_coupon_ask_qty,
                    POSITION_LIMITS[COUPON] - state.position.get(COUPON, 0),
                ]
            )
        )

    def compute_min_coupon_sell_qty(self, state: TradingState):
        # Min quantity of COUPON that can be sold
        best_coupon_bid, _ = self.get_best_bid(state, COUPON)
        available_coupon_bid_qty = sum(q for a, q in state.order_depths[COUPON].buy_orders.items() if a >= best_coupon_bid - 2)
        return math.ceil(
            max(
                [
                    available_coupon_bid_qty,
                    -POSITION_LIMITS[COUPON] - state.position.get(COUPON, 0),
                ]
            )
        )

    def run(self, state: TradingState):
        result = {}
        self.conversions = 0
        for product in ["AMETHYSTS", "STARFRUIT", "ORCHIDS", "GIFT_BASKET", COCONUT]:
            if product == "ORCHIDS":
                continue
                orders: List[Order] = []
                self.trade_orchids(state, orders)
                print("ORCHIDS orders", orders)
                result[product] = orders
            elif product in ["AMETHYSTS", "STARFRUIT"]:
                continue
                self.buys = 0
                self.sells = 0
                orders: List[Order] = []
                order_depth: OrderDepth = state.order_depths[product]
                current_position = state.position.get(product, 0)
                logger.print("Processing", product, "with current position", current_position)
                position_limit = 20  # Maximum allowable position (both long and short)
                if product == "AMETHYSTS":
                    midpoint = 10000  # Fixed midpoint for AMETHYSTS
                    self.process_market_trades(order_depth, orders, midpoint, current_position, position_limit, product)
                    self.process_neutral_trades(order_depth, product, orders, midpoint, current_position)
                elif product == "STARFRUIT":
                    midpoint = int(math.ceil((max(order_depth.sell_orders) + min(order_depth.buy_orders)) / 2))
                    logger.print("STARFRUIT midpoint", midpoint)
                    self.process_market_trades(order_depth, orders, midpoint, current_position, position_limit, product)
                    self.process_neutral_trades(order_depth, product, orders, midpoint, current_position)
                # Undercutting strategy: finding the next best buy and sell orders to undercut
                next_sell_order = next((price for price in sorted(order_depth.sell_orders) if price > midpoint), None)
                next_buy_order = next((price for price in sorted(order_depth.buy_orders, reverse=True) if price < midpoint), None)

                # Place undercutting orders if applicable
                if next_buy_order:
                    undercut_buy_price = next_buy_order + 1
                    if current_position <= position_limit:
                        max_buy_quantity = position_limit - current_position - self.buys
                        if max_buy_quantity > 0:
                            orders.append(Order(product, undercut_buy_price, max_buy_quantity))
                            logger.print("Undercutting buy order", product, undercut_buy_price, max_buy_quantity)

                if next_sell_order:
                    undercut_sell_price = next_sell_order - 1
                    if current_position >= -position_limit:
                        max_sell_quantity = -position_limit - current_position + self.sells
                        logger.print("Sells during market making", self.sells, "Buys during market making", self.buys)
                        if max_sell_quantity < 0:
                            orders.append(Order(product, undercut_sell_price, max_sell_quantity))
                            logger.print("Undercutting sell order", product, undercut_sell_price, max_sell_quantity)
                result[product] = orders
            elif product == "GIFT_BASKET":
                continue
                orders: List[Order] = []
                self.trade_baskets(state, orders)
                result["GIFT_BASKET"] = [o for o in orders if o.symbol == "GIFT_BASKET"]
                result["STRAWBERRIES"] = [o for o in orders if o.symbol == "STRAWBERRIES"]
                result["CHOCOLATE"] = [o for o in orders if o.symbol == "CHOCOLATE"]
                result["ROSES"] = [o for o in orders if o.symbol == "ROSES"]
            elif product == "COCONUT":
                orders: List[Order] = []
                self.trade_coconuts(state, orders)
                for o in orders:
                    if o.symbol not in result:
                        result[o.symbol] = []
                    result[o.symbol].append(o)

        traderData = "Updated State"  # Update the trader state for next iteration
        logger.flush(state, result, self.conversions, traderData)
        return result, self.conversions, traderData

    def trade_coconuts(self, state, orders):
        coconut_position = state.position.get(COCONUT, 0)
        coconut_buy_orders = state.order_depths[COCONUT].buy_orders
        coconut_sell_orders = state.order_depths[COCONUT].sell_orders
        sorted_coconut_bids = sorted(coconut_buy_orders.keys(), reverse=True)
        sorted_coconut_asks = sorted(coconut_sell_orders.keys())
        available_coconut_ask_qty = sum(q for a, q in coconut_sell_orders.items())
        available_coconut_bid_qty = sum(q for a, q in coconut_buy_orders.items())
        best_coconut_bid = sorted_coconut_bids[0] if sorted_coconut_bids else 0
        worst_coconut_bid = sorted_coconut_bids[-1] if sorted_coconut_bids else 0
        best_coconut_ask = sorted_coconut_asks[0] if sorted_coconut_asks else 999999
        worst_coconut_ask = sorted_coconut_asks[-1] if sorted_coconut_asks else 999999
        coconut_midprice = (best_coconut_bid + best_coconut_ask) / 2

        coupon_position = state.position.get(COUPON, 0)
        coupon_buy_orders = state.order_depths[COUPON].buy_orders
        coupon_sell_orders = state.order_depths[COUPON].sell_orders
        sorted_coupon_bids = sorted(coupon_buy_orders.keys(), reverse=True)
        sorted_coupon_asks = sorted(coupon_sell_orders.keys())
        best_coupon_bid = sorted_coupon_bids[0] if sorted_coupon_bids else 0
        best_coupon_ask = sorted_coupon_asks[0] if sorted_coupon_asks else 999999

        coupon_delta = compute_coconut_coupon_delta(coconut_midprice)[1]
        expected_coupon_price = (coconut_midprice - COCONUT_FMV) * coupon_delta + COUPON_FMV

        logger.print(f"Coconut midprice {coconut_midprice}")
        logger.print(f"Coupon delta {coupon_delta}")
        logger.print(f"Expected coupon price {expected_coupon_price}")
        logger.print(f"Best coupon bid {best_coupon_bid}, best coupon ask {best_coupon_ask}")
        logger.print(f"Best coconut bid {best_coconut_bid}, best coconut ask {best_coconut_ask}")
        logger.print(f"Coupon sell orders {coupon_sell_orders}")
        logger.print(f"Coupon buy orders {coupon_buy_orders}")

        coconut_trade_qty = 0
        coupon_trade_qty = 0
        coupon_price = 0
        if (best_coupon_bid - expected_coupon_price) / expected_coupon_price > TRADE_PERCENT_THRESHOLD:
            # Sell COUPON
            for b in sorted_coupon_bids:
                if (b - expected_coupon_price) / expected_coupon_price > TRADE_PERCENT_THRESHOLD:
                    coupon_trade_qty -= coupon_buy_orders[b]
                    coupon_price = b

            coupon_trade_qty = max(coupon_trade_qty, -POSITION_LIMITS[COUPON] - coupon_position)
            new_coupon_position = coupon_position + coupon_trade_qty

            desired_coconut_position = int(round(-new_coupon_position * coupon_delta))
            coconut_trade_qty = desired_coconut_position - coconut_position
            if desired_coconut_position > POSITION_LIMITS[COCONUT] or coconut_trade_qty > -available_coconut_ask_qty:
                coconut_trade_qty = min(POSITION_LIMITS[COCONUT] - coconut_position, -available_coconut_ask_qty)
                coupon_trade_qty = int(round(-(coconut_trade_qty / coupon_delta) - coupon_position))

        elif (best_coupon_ask - expected_coupon_price) / expected_coupon_price < -TRADE_PERCENT_THRESHOLD:
            # Buy COUPON
            for a in sorted_coupon_asks:
                if (a - expected_coupon_price) / expected_coupon_price < -TRADE_PERCENT_THRESHOLD:
                    coupon_trade_qty -= coupon_sell_orders[a]
                    coupon_price = a

            coupon_trade_qty = min(coupon_trade_qty, POSITION_LIMITS[COUPON] - coupon_position)
            new_coupon_position = coupon_position + coupon_trade_qty

            desired_coconut_position = int(round(-new_coupon_position * coupon_delta))
            coconut_trade_qty = desired_coconut_position - coconut_position
            if desired_coconut_position < -POSITION_LIMITS[COCONUT] or coconut_trade_qty < -available_coconut_bid_qty:
                coconut_trade_qty = max(-POSITION_LIMITS[COCONUT] - coconut_position, -available_coconut_bid_qty)
                coupon_trade_qty = int(round(-(coconut_trade_qty / coupon_delta) - coupon_position))

        orders.append(Order(COUPON, coupon_price, coupon_trade_qty))
        if coconut_trade_qty >= 0:
            orders.append(Order(COCONUT, worst_coconut_ask, coconut_trade_qty))
        else:
            orders.append(Order(COCONUT, worst_coconut_bid, coconut_trade_qty))

    def trade_baskets(self, state, orders):
        # Total profit: 347,136
        premium = 379.4904833333333
        premium_std_dev = 75.7054446667
        basket_buy_orders = state.order_depths["GIFT_BASKET"].buy_orders
        basket_sell_orders = state.order_depths["GIFT_BASKET"].sell_orders
        strawberry_buy_orders = state.order_depths["STRAWBERRIES"].buy_orders
        strawberry_sell_orders = state.order_depths["STRAWBERRIES"].sell_orders
        chocolate_buy_orders = state.order_depths["CHOCOLATE"].buy_orders
        chocolate_sell_orders = state.order_depths["CHOCOLATE"].sell_orders
        rose_buy_orders = state.order_depths["ROSES"].buy_orders
        rose_sell_orders = state.order_depths["ROSES"].sell_orders
        best_basket_bid, best_basket_bid_volume = max(basket_buy_orders.keys()), basket_buy_orders[max(basket_buy_orders.keys())]
        best_basket_ask, best_basket_ask_volume = min(basket_sell_orders.keys()), basket_sell_orders[min(basket_sell_orders.keys())]
        best_strawberry_bid, best_strawberry_bid_volume = max(strawberry_buy_orders.keys()), strawberry_buy_orders[max(strawberry_buy_orders.keys())]
        best_strawberry_ask, best_strawberry_ask_volume = min(strawberry_sell_orders.keys()), strawberry_sell_orders[min(strawberry_sell_orders.keys())]
        best_chocolate_bid, best_chocolate_bid_volume = max(chocolate_buy_orders.keys()), chocolate_buy_orders[max(chocolate_buy_orders.keys())]
        best_chocolate_ask, best_chocolate_ask_volume = min(chocolate_sell_orders.keys()), chocolate_sell_orders[min(chocolate_sell_orders.keys())]
        best_rose_bid, best_rose_bid_volume = max(rose_buy_orders.keys()), rose_buy_orders[max(rose_buy_orders.keys())]
        best_rose_ask, best_rose_ask_volume = min(rose_sell_orders.keys()), rose_sell_orders[min(rose_sell_orders.keys())]
        short_arbitrage_premium = best_basket_bid - best_chocolate_ask * 4 - best_strawberry_ask * 6 - best_rose_ask
        long_arbitrage_premium = best_basket_ask - best_chocolate_bid * 4 - best_strawberry_bid * 6 - best_rose_bid
        basket_position = state.position.get("GIFT_BASKET", 0)
        strawberry_position = state.position.get("STRAWBERRIES", 0)
        chocolate_position = state.position.get("CHOCOLATE", 0)
        rose_position = state.position.get("ROSES", 0)

        basket_buy_orders = 0
        basket_sell_orders = 0
        # (signal, limit, hedge)
        buy_signal = premium - (premium_std_dev * 0.7)
        sell_signal = premium + (premium_std_dev * 1)

        if long_arbitrage_premium < buy_signal:
            logger.print("LONG PREMIUM", best_basket_ask - 4 * best_chocolate_bid - 6 * best_strawberry_bid - best_rose_bid)
            logger.print("BEST BASKET ASK", best_basket_ask_volume)
            size = min(-best_basket_ask_volume, 58 - basket_position)

            orders.append(Order("GIFT_BASKET", best_basket_ask, size))
            orders.append(Order("CHOCOLATE", best_chocolate_bid, -size * 4))
            orders.append(Order("STRAWBERRIES", best_strawberry_bid, -size * 6))
            orders.append(Order("ROSES", best_rose_bid, -size))

        if short_arbitrage_premium > sell_signal:
            logger.print("SHORT PREMIUM", short_arbitrage_premium)
            size = max(-best_basket_bid_volume, -58 - basket_position)

            orders.append(Order("GIFT_BASKET", best_basket_bid, size))
            orders.append(Order("CHOCOLATE", best_chocolate_ask, -size * 4))
            orders.append(Order("STRAWBERRIES", best_strawberry_ask, -size * 6))
            orders.append(Order("ROSES", best_rose_ask, -size))

        if basket_position < 0:
            if strawberry_position < 6 * -basket_position:
                orders.append(Order("STRAWBERRIES", best_strawberry_ask, (6 * -basket_position) - strawberry_position))
            if chocolate_position < 4 * -basket_position:
                orders.append(Order("CHOCOLATE", best_chocolate_ask, (4 * -basket_position) - chocolate_position))
            if rose_position < -basket_position:
                orders.append(Order("ROSES", best_rose_ask, -basket_position - rose_position))
        if basket_position > 0:
            if strawberry_position > 6 * -basket_position:
                orders.append(Order("STRAWBERRIES", best_strawberry_bid, (6 * -basket_position) - strawberry_position))
            if chocolate_position > 4 * -basket_position:
                orders.append(Order("CHOCOLATE", best_chocolate_bid, (4 * -basket_position) - chocolate_position))
            if rose_position > -basket_position:
                orders.append(Order("ROSES", best_rose_bid, -basket_position - rose_position))

    def trade_orchids(self, state, orders):
        product = "ORCHIDS"
        current_position = state.position.get(product, 0)
        logger.print("Current position", current_position)
        if current_position != 0:
            logger.print("Buying from other island: ", abs(current_position), "ORCHIDS")
            self.conversions += -current_position

        if current_position == 0:
            logger.print("We bought ORCHIDS from other island, now looking to sell again")
        observations = state.observations.conversionObservations.get(product, None)
        if observations is None:
            return []
        conversion_ask_price = observations.askPrice
        conversion_bid_price = observations.bidPrice
        import_tariff = observations.importTariff
        export_tariff = observations.exportTariff
        transport_fees = observations.transportFees
        sunlight = observations.sunlight
        humidity = observations.humidity
        buy_orders = state.order_depths[product].buy_orders
        sell_orders = state.order_depths[product].sell_orders
        best_bid = max(buy_orders.keys())
        best_ask = min(sell_orders.keys())

        break_even_sell = conversion_ask_price + import_tariff + transport_fees
        whole_number_sell = conversion_bid_price % 1
        if whole_number_sell == 0:
            potential_sell_price = int(conversion_bid_price - 1)
        else:
            potential_sell_price = math.floor(conversion_bid_price)
        # Sell at a price higher than the break-even point that is below the midpoint
        sell_price = max(math.ceil(break_even_sell), potential_sell_price)
        logger.print("Selling ORCHIDS in own island at", sell_price)
        orders.append(Order(product, sell_price, -100))

        whole_number_buy = conversion_ask_price % 1
        if whole_number_buy == 0:
            potential_buy_price = int(conversion_ask_price + 1)
        else:
            potential_buy_price = math.ceil(conversion_ask_price)
        break_even_buy = conversion_bid_price - export_tariff - transport_fees
        # Buy at a price lower than the break-even point that is above the midpoint
        buy_price = min(math.floor(break_even_buy), potential_buy_price)
        logger.print("Buying ORCHIDS in own island at", buy_price)
        orders.append(Order(product, buy_price, 100))

    def process_neutral_trades(self, order_depth, product, orders, midpoint, current_position):
        """Specific processing for product to neutralize position at the midpoint."""
        # Neutralizing strategy at the midpoint of 10000
        if midpoint in order_depth.sell_orders and current_position < 0:
            # Neutralize negative position
            neutralize_quantity = -order_depth.sell_orders[midpoint]
            if current_position < 0 and current_position + neutralize_quantity < abs(current_position):
                orders.append(Order(product, midpoint, neutralize_quantity))
                logger.print("Neutralizing buy", neutralize_quantity, "product at midpoint")
                self.buys += neutralize_quantity
                current_position += neutralize_quantity

        if midpoint in order_depth.buy_orders and current_position > 0:
            # Neutralize positive position
            neutralize_quantity = order_depth.buy_orders[midpoint]
            if current_position > 0 and abs(current_position - neutralize_quantity) < current_position:
                orders.append(Order(product, midpoint, -neutralize_quantity))
                logger.print("Neutralizing sell", neutralize_quantity, "product at midpoint")
                self.sells += neutralize_quantity
                current_position -= neutralize_quantity
        return current_position

    def process_market_trades(self, order_depth, orders, midpoint, current_position, position_limit, product):
        """Generic market trade processing for all products."""
        # Buy below the midpoint
        for price, quantity in sorted(order_depth.sell_orders.items()):
            if price < midpoint:
                logger.print("BUYING at", price, "quantity", quantity, "current_position", current_position, "position_limit", position_limit)
                max_buy_quantity = min(-quantity, position_limit - current_position)
                logger.print("MAX BUY COMPARISION", -quantity, position_limit - current_position, max_buy_quantity)
                if max_buy_quantity > 0:
                    orders.append(Order(product, price, max_buy_quantity))
                    self.buys += max_buy_quantity
                    logger.print("Buys", self.buys, "at", price)
                    logger.print("Buying", max_buy_quantity, product, "at", price)
                    current_position += max_buy_quantity

        # Sell above the midpoint
        for price, quantity in sorted(order_depth.buy_orders.items(), reverse=True):
            if price > midpoint:
                max_sell_quantity = min(quantity, position_limit + current_position)
                if max_sell_quantity > 0:
                    orders.append(Order(product, price, -max_sell_quantity))
                    self.sells += max_sell_quantity
                    logger.print("Sells", self.buys, "at", price)
                    logger.print("Selling", max_sell_quantity, product, "at", price)
                    current_position -= max_sell_quantity
        return current_position
