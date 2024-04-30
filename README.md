This is Cove Capital's repository for IMC Prosperity 2. We placed #[TBD] out of [TBD] teams internationally, and #[TBD] in the United States. Below is a breakdown of our strategies and thoughts when approaching this challenge:
##########################################

`ROUND 1`:

We unfortunately lost our code after this round because did not use GitHub well at the time, so I do not have the code we submitted for `Round 1` Algorithmic Challenge. I tried to mimic our ideas for the manual challenge, but for the algorithmic I didn't want to write it again so I just used Stanford Cardinals code from last year, but with the hyperparameters I believe were closer to our values. I didn't look to close into their code, so I won't take credit for it - just put it in there for completeness of this repository.

ALGORITHMIC:

- The first two tradable products are introduced: `STARFRUIT` and `AMETHYSTS`. While the value of the `AMETHYSTS` has been stable throughout the history of the archipelago, the value of `STARFRUIT` has been going up and down over time. Develop your initial trading strategy and write your first Python program to get off to a good start in this world of trading and market making. Even if the price of a product moves very little or in a very unpredictable way, there might still be clever ways to profit if you both buy and sell. Position limits for the newly introduced products:
    - `STARFRUIT`: 20
    - `AMETHYSTS`: 20


Reading this it was pretty apparent to us that `AMETHYST` fair value was going to be pretty constant and easily tradeable around. People in the Discord were sending out Stanford Cardinal's code last year which we took a look at and actually found pretty similar to our findings, confirming that we were on the right track. We decided to learn a little more on what market-taking and market-making were and actually recognized that `STARFRUIT` could use the exact same strategy. The only reason that it is viable to use the same strategy for `STARFRUIT` is because we found that the fair value of it was just (worst_ask - worst_bid) / 2, meaning we always knew the right price.

We also implemented a way to reduce our risk to massive moves in the market for `STARFRUIT` by continuously neutralizing our position if people were willing to buy/sell at the fair price and we were already staked on the other side of that trade.

KEY TRADING STRATEGIES: Market Making, Market Taking, Risk Aversion Rebalancing

MANUAL:

- With a large school of goldfish visiting, an opportunity arises to acquire some top grade `SCUBA_GEAR`. You only have two chances to offer a good price. Each one of the goldfish will accept the lowest bid that is over their reserve price. You know there’s a constant desire for scuba gear on the archipelago. So, at the end of the round, you’ll be able to sell them for 1000 SeaShells ****a piece. Whilst not every goldfish has the same reserve price, you know the distribution of their reserve prices. The reserve price will be no lower than 900 and no higher than 1000. The probability scales linearly from 0 at 900 to most likely at 1000. You only trade with the goldfish. Bids of other participants will not affect your results.


This round we really just tried to become familiar with the interface and actually understand the fundamentals of how this game worked. I immediately got started on the manual challenge because it popped out to me like an optimization problem that dealt with probabilities and payout functions. After a few hours, I had a firm understanding that our maximum payoff really was finding the payoff of the second bid and then maximizing the first bid based on that. Using some python, I turned the mathematics into code and was pretty confident in the answer.


At the end of `ROUND 1`, we were ranked #109 Overall.


###########################################

`ROUND 2`:

ALGORITHMIC:

- During this second round of the Prosperity challenge, you again get the chance to trade the same products as in round 1. In addition, a new product is introduced: `ORCHIDS`. `ORCHIDS` are very delicate and their value is dependent on all sorts of observable factors like hours of sun light, humidity, shipping costs, in- & export tariffs and suitable storage space. Can you find the right connections to optimize your program?

Position limits for the newly introduced products:
    - `ORCHIDS`: 100

This round was really really cool. However, we were not so happy that we got #109 last round, so first order of business was looking at the logs and seeing where we messed up. We recognized pretty quickly, our market making was not getting hit because we were not putting our orders in correctly. On top of that, our order sizes exceeded the limit sometimes, cancelling all orders (a definite way to lose this competition). This fix took us a little bit, but we felt pretty confident in our strategy going forward.

Now to orchids. Orchids had a lot of new info: Sunlight, Humidity, Tariffs, Conversion Prices, etc. We spent HOURS on sunlight and humidity because the correlation between them and price was very high. This got us nowhere and we were thinking that maybe the idea behind this challenge was not to trade direction, but instead trade on arbitrage between our island's market and the other island's market. This is where we hit gold. All we had to do was calculate the price in which it was profitable to make a trade on our island, set an order that seemed favorable for the bots that still guarenteed us profit, and then immediately sell it to the other island, leaving us with zero directional risk. We wrote up the code, which was pretty short and decided to ship it after doing well on the backtester.


MANUAL:

- You get the chance to do a series of trades in some foreign island currencies. The first trade is a conversion of your SeaShells into a foreign currency, the last trade is a conversion from a foreign currency into SeaShells. Everything in between is up to you. Give some thought to what series of trades you would like to do, as there might be an opportunity to walk away with more shells than you arrived with.

To anyone who has taken Linear Algebra (or has ChatGPT lol), this is a pretty straightforward matrix calculation. You can also bruteforce a solution by looping through the entire search space and printing the combination that gives the max profit. We finished this in about 5 minutes.

At the end of `ROUND 2` we were #7 Overall. Our group chat that morning was filled with positive vibes.

#############################################

`ROUND 3`:

ALGORITHMIC:

- Cupid has landed in our archipelago and infected almost every inhabitant. Next to the products from the previous two rounds, the `GIFT_BASKET` is now available as a tradable good. This lovely basket contains three things: 

1. Four `CHOCOLATE` bars
2. Six `STRAWBERRIES`
3. A single `ROSES`

This challenge was really difficult. Our not-so-deep knowledge of trading ideas really got to us, as I'll explain.

We first plotted the data and noticed that a gift basket was always more expensive than the combination of the independent items. We also noticed that individual items really didn't follow each others prices (a.k.a a move in `STRAWBERRIES` did not indicate a move in `CHOCOLATE`). We found a high correlation between gift baskets and the combination of independent items, but it wasn't perfect correlation, which made us curious if there was any potential trading strategies there. We decided to analyse how the premium of baskets changed over the days of data given and it looked pretty normally distributed (even though no normal distribution test said it was normal). So, we figured that even if it wasn't the main strategy, we might as well just trade the premium if it falls below or above the mean premium price. This strategy actually made us a lot of money and we started to believe that this was actually what we should be trading on, but because of that we started to overfit the data. We couldn't answer questions like:

- What price level should we buy/sell at?
- Should we perfectly hedge gift baskets with it's components?
- How do we actually calculate the mean gift basket price (rolling mean, set mean)?

These questions were really difficult to answer and all of them depended on each other. Using the backtester scared us because it just felt like we were trying to maximize the profits, which meant overfit. We kind of went into a fury of trying things out and one of the teammates noticed that no matter what, we always lose money if we hedge with the products. I was confused on why we wouldn't hedge since then we are assuming that the price of the premium indicates the price of gift baskets, but they seemed very confident. We really didn't know how to set the buy/sell price levels and I read a few research papers but all were pretty complex and I didn't see an exact application we could put into our code. We looked at Bollinger Bands, multiple price levels, a slowing factor in our order size, but at the end we decided to stay simple, use the data to find the mean and std. dev, and set a price level of around 1 std dev.

MANUAL:

- A mysterious treasure map and accompanying note has everyone acting like heroic adventurers. You get to go on a maximum of three expeditions to search for treasure. Your first expedition is free, but the second and third one will come at a cost. Keep in mind that you are not the only one searching and you’ll have to split the spoils with all the others that search in the same spot. Plan your expeditions carefully and you might return with the biggest loot of all. 

Here's a breakdown of how your profit from an expedition will be computed:
Every spot has its **treasure multiplier** (up to 100) and the number of **hunters** (up to 8). The spot's total treasure is the product of the **base treasure** (7500, same for all spots) and the spot's specific treasure multiplier. However, the resulting amount is then divided by the sum of the hunters and the percentage of all the expeditions (from other players) that took place there. For example, if a field has 5 hunters, and 10% of all the expeditions (from all the other players) are also going there, the prize you get from that field will be divided by 15. After the division, **expedition costs** apply (if there are any), and profit is what remains.

Second and third expeditions are optional: you are not required to do all 3. Fee for embarking upon a second expedition is 25 000, and for third it's 75 000. Order of submitted expeditions does not matter for grading.

For this part, we knew that there was only so much mathematics we could do and just had to rely on sentiment of the Discord to get an understanding of how people would place their bets. We did an iteration simulator that showed the best options based on how deep people would go. For example, if everyone calculates the best values on face value and choose it, what should we choose. Then assume almost everyone just did that (an iteration) and will diverge like us - now what is the best option? We really couldn't come to a consensus so we ended up choosing the second best values and shipped it. Turns out a lot of people like the number 73 (one of the ones we chose) so one of our options was great, but 73 was really really bad (like the worst option).

At the end of `ROUND 3` we were #14 overall.

########################################################


`ROUND 4`:

- Our inhabitants are crazy about coconuts. So crazy even, that they invented a new tradable good, `COCONUT_COUPON`. The coupons will give you the right to buy `COCONUT` at a certain price by the end of the round and can be traded as a separate good. Of course you will have to pay a premium for these coupons, but if you play your coconuts right, SeaShells spoils will be waiting for you on the horizon.

Coconut Coupons give the right to buy Coconut at a certain price at some time in future. Certain price = 10000 and some time in future = 250 trading days, each round is 1 trading day.

Position limits for the newly introduced products:

    - `COCONUT`: 300
    - `COCONUT_COUPON`: 600

Derivatives! This round had some information that was different in the Wiki compared to the video (which actually played into my favor) which confused us at first. The key thing I didn't understand was what the 376.63 expiration was in the video since it 
