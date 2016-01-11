import logging
import os
from colour import Color
from market import realstring_dict, get_long_short_term_averages
from pw_client import PWClient, LeanPWDB
from bson.objectid import ObjectId
from slack import post_good_buy, post_good_buy_offer, post_good_sell

money_string = '<b style="color: #28d020;">$</b>'
img_dict = {'steel': 'https://politicsandwar.com/img/resources/steel.png', 'oil': 'https://politicsandwar.com/img/resources/oil.png', 'aluminum': 'https://politicsandwar.com/img/resources/aluminum.png', 'lead': 'https://politicsandwar.com/img/resources/lead.png', 'bauxite': 'https://politicsandwar.com/img/resources/bauxite.png', 'food': 'https://politicsandwar.com/img/icons/16/steak_meat.png', 'money': 'https://politicsandwar.com/img/resources/money.png', 'munition': 'https://politicsandwar.com/img/resources/munitions.png', 'uranium': 'https://politicsandwar.com/img/resources/uranium.png', 'coal': 'https://politicsandwar.com/img/resources/coal.png', 'iron': 'https://politicsandwar.com/img/resources/iron.png', 'gasoline': 'https://politicsandwar.com/img/resources/gasoline.png'}

def make_trade_url(good, ascending=True, sell=True):
    if sell:
        buysell = "sell"
    else:
        buysell = "buy"

    if ascending:
        asc_desc = "ASC"
    else:
        asc_desc = "DESC"
    return "https://politicsandwar.com/index.php?id=90&display=world&resource1=" + good + "&buysell=" + buysell +\
           "&ob=price&od=" + asc_desc + "&maximum=15&minimum=0&search=Go"


logger = logging.getLogger("pwc")
fhandler1 = logging.FileHandler("city_check.out", mode='w')
logger.addHandler(fhandler1)
logger.setLevel(logging.DEBUG)

USERNAME = os.environ['PW_USER']
PASS = os.environ['PW_PASS']
pwc = PWClient(USERNAME, PASS, logger=logger)
pwdb = LeanPWDB()

sky_blue = Color("#2b8dcc")
dark_blue = Color("#0d2b3e")

light_orange = Color("#FF7B0C")
dark_orange = Color("#7F4108")

orange_gradient = list(dark_orange.range_to(light_orange, 100))
blue_gradient = list(dark_blue.range_to(sky_blue, 100))

resource_dict = {}
for item_type in realstring_dict.keys():
    resource_dict[item_type] = {"buy": 0,
                                "sell": 0}

# get the buy high values
for item_type in realstring_dict.keys():
    item_value = realstring_dict[item_type]
    trade_url = "https://politicsandwar.com/index.php?id=90&display=world&resource1="+item_value+"&buysell=buy&ob=price&od=DESC&maximum=15&minimum=0&search=Go"
    nationtable = pwc._retrieve_nationtable(trade_url, 0)
    trade_tr = nationtable.findall(".//tr")[1]
    trade_td = trade_tr.findall(".//td")[5]
    trade_text = trade_td[0].text
    trade_num = int(trade_text.split("/")[0].replace(",",""))
    resource_dict[item_type]["buy"] = trade_num

# get the sell high values
for item_type in realstring_dict.keys():
    item_value = realstring_dict[item_type]
    trade_url = "https://politicsandwar.com/index.php?id=90&display=world&resource1="+item_value+"&buysell=sell&ob=price&od=ASC&maximum=15&minimum=0&search=Go"
    nationtable = pwc._retrieve_nationtable(trade_url, 0)
    trade_tr = nationtable.findall(".//tr")[1]
    trade_td = trade_tr.findall(".//td")[5]
    trade_text = trade_td[0].text
    trade_num = int(trade_text.split("/")[0].replace(",",""))
    resource_dict[item_type]["sell"] = trade_num

result = pwdb.add_market_watch_record(resource_dict)

lta, sta = get_long_short_term_averages(pwdb)

# Generate charts

html_string = "<table border='1' rules='all'>\n"
html_string += \
    "<tr>" \
    "<th>Resource</th>" \
    "<th>Current (low) sell price</th>" \
    "<th>Average (low) sell price</th>" \
    "<th>Percent difference</th>" \
    "</tr>\n"

buys_higher_than_avg_sells = {}

for item_type in realstring_dict.keys():
    # Make judgements on sells

    current_sell = resource_dict[item_type]["sell"]
    average_sell = lta[-1][item_type + "avg_sell"]
    sell_diffp = (abs(lta[-1][item_type+"avg_sell"] - resource_dict[item_type]["sell"]) / (.5 * (lta[-1][item_type + "avg_sell"] + resource_dict[item_type]["sell"]))) * 100
    gradient_index = 0
    if sell_diffp > 25:
        gradient_index = 99
    else:
        gradient_index = int(100 * float(sell_diffp) / 25.0)
        if gradient_index >= 100:
            gradient_index = 99

    if average_sell > current_sell:
        sell_color = str(blue_gradient[gradient_index])
        if sell_diffp >= 25.0:
            if pwdb.increment_buy_counter_for_type(item_type, sell_diffp):
                pass # TODO: this
                # post_good_buy(realstring_dict[item_type], make_trade_url(realstring_dict[item_type]), average_sell, current_sell, image_url=plot_urls[item_type]+".png")
        else:
            pwdb.reset_buy_counter(item_type)
        sell_diffp *= -1
    else:
        if sell_diffp >= 25.0:
            if pwdb.increment_sell_counter_for_type(item_type, sell_diffp):
                pass # TODO: this
                # post_good_sell(realstring_dict[item_type], make_trade_url(realstring_dict[item_type]), average_sell, current_sell, image_url=plot_urls[item_type]+".png")
        else:
            pwdb.reset_sell_counter(item_type)
        sell_color = str(orange_gradient[gradient_index])

    current_buy = resource_dict[item_type]["buy"]
    if current_buy > average_sell:
        buys_higher_than_avg_sells[item_type] = current_buy
    else:
        buys_higher_than_avg_sells[item_type] = -1

    buy_diffp = (abs(lta[-1][item_type + "avg_buy"] - resource_dict[item_type]["buy"]) / (.5 * (lta[-1][item_type + "avg_buy"] + resource_dict[item_type]["buy"]))) * 100
    html_string += "<tr>" \
                   "<td>"+realstring_dict[item_type].capitalize()+"</td>" \
                   "<td style='color:"+sell_color+";'>"+str(current_sell)+"</td>" \
                   "<td style='color:"+sell_color+";'>"+str(average_sell)+"</td>" \
                   "<td style='color:"+sell_color+";'>"+str(sell_diffp)+"</td>" \
                   "</tr>"
html_string += "</table>"
print html_string

# Print buy anomalies
for key in buys_higher_than_avg_sells.keys():
    if buys_higher_than_avg_sells[key] < 0:
        pwdb.reset_buy_offer_counter(key)
    else:
        html_string += "<h3>There is a buy offer for"+str(key)+ "("+str(buys_higher_than_avg_sells[key])+") that exceeds the average sell price! Take this trade!</h3>"
        good = realstring_dict[key]
        good_url = make_trade_url(good, ascending=False, sell=False)
        if pwdb.increment_buy_offer_counter_for_type(key):
            pass # TODO: this
            # post_good_buy_offer(good, good_url, averages[key]["sell"], buys_higher_than_avg_sells[key])
