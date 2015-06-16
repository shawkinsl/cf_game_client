from income_tracker import owed_key, collected_key
from pnw_db import PWDB, turns_since_collected_key
import copy
import datetime

__author__ = 'sxh112430'
import os

class RequestBot:

    def __init__(self):
        if 'PWUSER' in os.environ:
            USERNAME = os.environ['PWUSER']
            PASS = os.environ['PWPASS']
        else:
            with open("/var/www/falcon/auth") as uf:
                USERNAME = uf.readline().strip()
                PASS = uf.readline().strip()
        __username = USERNAME
        __pass = PASS
        self.pwdb = PWDB(__username, __pass, skip_pwclient=True)

    def make_request(self, nation_id):
        nation_id = str(nation_id).strip()
        nation_tax_db = self.pwdb.get_nation(nation_id)

        money_owed =        nation_tax_db[owed_key]['money']
        food_owed =         nation_tax_db[owed_key]['food']
        coal_owed =         nation_tax_db[owed_key]['coal']
        uranium_owed =      nation_tax_db[owed_key]['uranium']
        oil_owed =          nation_tax_db[owed_key]['oil']
        lead_owed =         nation_tax_db[owed_key]['lead']
        iron_owed =         nation_tax_db[owed_key]['iron']
        bauxite_owed =      nation_tax_db[owed_key]['bauxite']
        gasoline_owed =     nation_tax_db[owed_key]['gasoline']
        munitions_owed =    nation_tax_db[owed_key]['munition']
        steel_owed =        nation_tax_db[owed_key]['steel']
        aluminum_owed =     nation_tax_db[owed_key]['aluminum']

        result = copy.copy(nation_tax_db[owed_key])
        nation_tax_db[owed_key]['money'] =    0
        nation_tax_db[owed_key]['food'] =     0
        nation_tax_db[owed_key]['coal'] =     0
        nation_tax_db[owed_key]['uranium'] =  0
        nation_tax_db[owed_key]['oil'] =      0
        nation_tax_db[owed_key]['lead'] =     0
        nation_tax_db[owed_key]['iron'] =     0
        nation_tax_db[owed_key]['bauxite'] =  0
        nation_tax_db[owed_key]['gasoline'] = 0
        nation_tax_db[owed_key]['munition'] = 0
        nation_tax_db[owed_key]['steel'] =    0
        nation_tax_db[owed_key]['aluminum'] = 0

        nation_tax_db[collected_key] = datetime.datetime.now() + datetime.timedelta(hours=2)
        nation_tax_db[turns_since_collected_key] = 0

        self.pwdb.set_nation(nation_id, nation_tax_db)

        self.pwdb._init_pwc()

        self.pwdb.pwc.make_bank_withdrawal(nation_id, money=money_owed, food=food_owed, coal=coal_owed, uranium=uranium_owed,
                                      oil=oil_owed, lead=lead_owed, iron=iron_owed, bauxite=bauxite_owed,
                                      gasoline=gasoline_owed, munitions=munitions_owed, steel=steel_owed,
                                      aluminum=aluminum_owed)

        return result
