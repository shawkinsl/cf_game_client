from datetime import datetime, timedelta
from pnw_db import PWDB
from pw_client import PWClient, DEBUG_LEVEL_MEGA_VERBOSE, DEBUG_LEVEL_STFU
import os
from pnw_db import rsc_key, score_diff_key, collected_key, can_collect_key, total_paid_key, owed_key

__author__ = 'sxh112430'

MAX_COLLECTION_TIMEDELTA = timedelta(days=3)
BASE_TAX = 1

class IncomeTracker:
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
        pwdb = PWDB(__username, __pass)
        pwc = pwdb.pwc
        assert isinstance(pwc, PWClient)

        pwc.debug = DEBUG_LEVEL_STFU
        records = pwc.get_alliance_tax_records_from_id(1356, only_last_turn=True)

        for record in records:
            if str(record['sender']).strip() == str(17270):
                print record

        average_score = pwc.get_alliance_average_score_from_id(1356)
        total_score = pwc.get_alliance_score_from_id(1356)

        ACTUAL_TOTAL = {}
        # For testing
        for record in records:
            for resource_type in record[rsc_key].keys():
                if resource_type not in ACTUAL_TOTAL.keys():
                    ACTUAL_TOTAL[resource_type] = 0
                ACTUAL_TOTAL[resource_type] += record[rsc_key][resource_type]

        # Get the lowest difference (negative) so we can keep everything else positive
        min_difference = 0
        for record in records:
            nation_obj = pwc.get_nation_obj_from_ID(record['sender'])
            record['nation_obj'] = nation_obj
            record[score_diff_key] = nation_obj.score - average_score
            if record[score_diff_key] < min_difference:
                min_difference = record[score_diff_key]

        # move everything to positive
        for record in records:
            record[score_diff_key] += min_difference * 3  # Move everything up to positive
            record[score_diff_key] *= record[score_diff_key]  # square it

        # Places where we will keep track of stuff
        # This is the total amount of stuff collected
        total_collected_this_turn = {}
        # This is how much was returned to little nations
        total_returned_from_collected = {}
        # This tracks how much was retained by each nation
        total_retained_this_turn = {}

        # Apply baserate
        for record in records:
            nation_id = record['sender']
            nation_tax_db = pwdb.get_nation(nation_id)
            last_collected_date = nation_tax_db[collected_key]

            record[can_collect_key] = True
            if pwc.get_current_date_in_datetime() - last_collected_date > MAX_COLLECTION_TIMEDELTA:
                record[can_collect_key] = False

            resources = record[rsc_key]

            # Auto-take baserate
            for resource_type in resources.keys():
                if resource_type not in total_collected_this_turn.keys():
                    total_collected_this_turn[resource_type] = 0

                if resource_type not in total_returned_from_collected.keys():
                    total_returned_from_collected[resource_type] = 0

                if resource_type not in total_retained_this_turn.keys():
                    total_retained_this_turn[resource_type] = 0

                if resource_type not in nation_tax_db[owed_key].keys():
                    nation_tax_db[owed_key][resource_type] = 0

                if resource_type not in nation_tax_db[total_paid_key].keys():
                    nation_tax_db[total_paid_key][resource_type] = 0

                amount_sent = resources[resource_type]  # Total sent in
                nation_tax_db[total_paid_key][resource_type] = amount_sent

                # Decide to take tax rate or 100%
                amount_collected = amount_sent * BASE_TAX
                if not record[can_collect_key]:
                    amount_collected = amount_sent  # collect 100%

                # Register how much was collected
                total_collected_this_turn[resource_type] += amount_collected
                if record[can_collect_key]:
                    nation_tax_db[owed_key][resource_type] += amount_sent - amount_collected
                    total_retained_this_turn[resource_type] += amount_sent - amount_collected

            pwdb.set_nation(nation_id, nation_tax_db)

            if str(record['sender']).strip() == str(17270):
                print record
                print "first set: ", pwdb.get_nation(nation_id)

        # Determine who is still owed from reserves
        collectors = [record for record in records if record[can_collect_key]
                      and not record['nation_obj'].color.strip() == "Gray"]

        """
        Differential percentage is a metric that calculates the "percent difference" you are away from the alliance score
        average. Everything is moved such that all differences are considered "positive," which sets the highest player at
        "zero." This way, everyone collects, but those who are on the lower end collect much more than those on the higher end.
        """

        # Only include collectors in diff sum
        differential_sum = 0
        for record in collectors:
            differential_sum += record[score_diff_key]


        sum_diff_percentage = 0

        for record in collectors:

            nation_id = record['sender']
            nation_tax_db = pwdb.get_nation(nation_id)

            diff_percentage = record[score_diff_key] / differential_sum
            print nation_id, "gets", diff_percentage, "%"
            sum_diff_percentage += diff_percentage
            owed_percentage = 0.5 * diff_percentage
            resources = record[rsc_key]
            for resource_type in total_collected_this_turn.keys():
                amount = total_collected_this_turn[resource_type]
                amount_owed = amount * owed_percentage
                nation_tax_db[owed_key][resource_type] += amount_owed
                total_returned_from_collected[resource_type] += amount_owed

            pwdb.set_nation(nation_id, nation_tax_db)

            if str(record['sender']).strip() == str(17270):
                print record
                print "second set: ", pwdb.get_nation(nation_id)

        # print "Diff percent total: ",sum_diff_percentage

        # for key in ACTUAL_TOTAL.keys():
            # print "         ", key
            # print "actual   ", ACTUAL_TOTAL[key]
            # print "collected", total_collected_this_turn[key]
            # print "returned ", total_returned_from_collected[key]
            # print "retained ", total_retained_this_turn[key]
            #
            # # Inputs equaled output
            # print "==?"
            # print total_retained_this_turn[key] + total_collected_this_turn[key]
            # print ACTUAL_TOTAL[key]