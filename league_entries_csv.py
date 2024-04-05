"""
This script uses the Riot Developer API to retrieve LeagueEntryDTO objects via the LEAGUE-v4 endpoint. A variety
of calls will be used within the endpoint depending on the specified tier. Tiers without divisions such as
Challenger have a unique call.

Author: Alex Nirenovic
"""

import requests
import pandas as pd
from pprint import pprint
from datetime import date, datetime
import sys
import os
import json

if os.path.isfile('api_key.txt'):
    with open('api_key.txt', 'r') as api_key_file:
        api_key = api_key_file.read().strip()
else:
    api_key = ''

REGIONS = ['br1', 'eun1', 'euw1', 'jp1', 'kr', 'la1', 'la2', 'na1', 'oc1', 'ph2', 'ru', 'sg2', 'th2', 'tr1',
           'tw2', 'vn2']

QUEUES = [
    'RANKED_SOLO_5x5',
    'RANKED_FLEX_SR',
    'RANKED_FLEX_TT'
]
TIERS = [
    'IRON',
    'BRONZE',
    'SILVER',
    'GOLD',
    'PLATINUM',
    'EMERALD',
    'DIAMOND',
    'MASTER',
    'GRANDMASTER',
    'CHALLENGER'
]
DIVISIONS = [
    'I',
    'II',
    'III',
    'IV'
]


def is_special_tier(tier):
    return tier in TIERS[TIERS.index('MASTER'):TIERS.index('CHALLENGER') + 1]


# This function generates a CSV of player
def get_league_entries_as_csv(region: str, queue: str, tier: str, divisions: list[str], get_all: str):
    # check arguments
    # init error message variable
    err = ''
    # valid queue
    if queue not in QUEUES:
        err += 'Invalid queue "' + queue + '". Options: ' + str(QUEUES) + '\n'
    # valid tier
    if tier not in TIERS:
        err += 'Invalid tier "' + tier + '". Options: ' + str(TIERS) + '\n'
    # check validity of all specified divisions, if tier chosen has divisions
    if tier not in TIERS[TIERS.index('MASTER'):TIERS.index('CHALLENGER') + 1]:
        invalid_divs = []
        # no divisions specified
        if len(divisions) == 0:
            err += 'No divisions specified. Options: ' + str(DIVISIONS) + '\n'
        else:
            for division in divisions:
                if division not in DIVISIONS:
                    invalid_divs.append(division)
            if len(invalid_divs) > 0:
                err += 'Invalid division'
                if len(invalid_divs) > 1:
                    err += 's'
                err += ': "' + str(invalid_divs) + '". Options: ' + str(DIVISIONS) + '\n'
                err += 'Separate multiple divisions by comma. Example: "I, IV" will return "I" and "IV" only.\n'
    if get_all != 'True' and get_all != 'False':
        err += ('Invalid option for "get all"(returns all pages of results if "True", or only first if "False").' +
                'Options: "True" or "False".')

    if err == '':
        # initialise variables for keeping track of current page of results
        more_results = True
        page = 1
        # track divisions if provided/applicable
        current_division = ''
        if len(divisions) > 0:
            more_divisions = True
            current_division = divisions[0]
        # empty list to store results
        result = []

        # the inner loop will execute fully, once per element in the list of divisions specified
        # this will get all entries, all pages (if get_all is True, first page only if false)
        while more_results:
            # construct the request URL using the provided arguments
            if is_special_tier(tier):
                url = ('https://' + region + '.api.riotgames.com/lol/league/v4/' + tier.lower() +
                       'leagues/by-queue/' + queue)
            else:
                url = ('https://' + region + '.api.riotgames.com/lol/league/v4/entries/' + queue + '/' + tier +
                       '/' + current_division + '/')
            url += '?page=' + str(page) + '&api_key=' + api_key
            # the below print command provides a text output updating on current progress as loop iterates
            print('Getting entries for ' + tier + ' ' + current_division + ' (' + queue + '), Page: ' +
                  str(page) + '...')
            resp = requests.get(url).json()
            # append result if not empty
            if len(resp) > 0:
                result.append(resp)
                # break if special tier, as they do not have multiple pages
                if is_special_tier(tier):
                    break
                # iterate page count if get_all is True
                if get_all == 'True':
                    page += 1
                # if get_all is False, only the first page is needed and loop will break
                elif get_all == 'False' and len(divisions) <= 1:
                    break
                elif get_all == 'False' and len(divisions) > 1 and current_division != divisions[-1]:
                    current_division = divisions[divisions.index(current_division) + 1]
                else:
                    break
            # if an empty response is returned, this means end of result pages. Check to increment count or break
            else:
                # if special tier, end of results
                if is_special_tier(tier):
                    print('and is special tier')
                    more_results = False
                # if not special tier, but end of last division, end of results
                elif current_division == divisions[-1]:
                    more_results = False
                # if not special tier, and more divisions, continue and reset counters
                else:
                    # next division
                    current_division = divisions[divisions.index(current_division) + 1]
                    # rest page to 1 for next division
                    page = 1

        # format division info for filename, e.g. 1 division: "_III_" multiple: "_II-IV"
        if len(divisions) > 1:
            filename_divisions = ''
            for division in divisions:
                filename_divisions += division
                if division != divisions[-1]:
                    filename_divisions += '-'
        else:
            filename_divisions = 'TIER'

        # format pages info for filename
        if is_special_tier(tier):
            filename_pages = 'ALL'
        elif get_all == 'True':
            filename_pages = 'PAGES-ALL'
        elif get_all == 'False':
            filename_pages = 'PAGE-1'
        else:
            filename_pages = 'PAGES-UNSPECIFIED'

        # generate formatted filename
        filename = ('league_data_' + tier + '_' + filename_divisions + '_' + filename_pages + '_' +
                    str(datetime.now().strftime("%Y-%m-%d_%H-%M")) + '.csv')
        # init empty dataframe
        data = pd.DataFrame()
        # iterate through pages, each containing the player objects (LeagueEntryDTO)
        if is_special_tier(tier):
            result = result[0]['entries']
            for entry in result:
                data = pd.concat([data, pd.DataFrame([entry])])
        else:
            for page in result:
                # for each individual player object in the page of results
                for entry in page:
                    # add player info to new row in dataframe
                    data = pd.concat([data, pd.DataFrame([entry])])
        # generate CSV from data
        data.to_csv(filename, mode='w', header=True)
        print(filename + ' successfully generated.')
    else:
        err += '\nNote: parameter arguments are CASE SENSITIVE.'
        print(err)


if __name__ == "__main__":
    args = sys.argv

    if len(args) == 4 and is_special_tier(args[3]):
        get_league_entries_as_csv(region=args[1], queue=args[2], tier=args[3], divisions=[],
                                  get_all='True')
    elif len(args) == 6 and not is_special_tier(args[3]):
        get_league_entries_as_csv(region=args[1], queue=args[2], tier=args[3], divisions=args[4].split(','),
                                  get_all=args[5])
    else:
        print('Incorrect arguments. Format: <region> <queue> <tier> <divisions> <get all>')
        print('Arguments provided: ' + str(args))
        print('\tOptions: ')
        print('\tRegions: ' + str(REGIONS))
        print('\tQueues: ' + str(QUEUES))
        print('\tTiers: ' + str(TIERS))
        print('\tDivisions: ' + str(DIVISIONS))
        print('\t(Divisions must be provided if Tier is NOT "MASTER" or "GRANDMASTER" or "CHALLENGER".' +
              'Otherwise, do not provide divisions argument.)')
        print('\tGet All: "True" or "False"')
        print('\t(IGNORE "Get all" argument if Tier is "MASTER" or "GRANDMASTER" or "CHALLENGER"')
        print('\tExample A: python league_entries.py "oc1" "RANKED_SOLO_5x5" "SILVER" "I,II,III,IV" "True"')
        print('\tExample B: python league_entries.py "oc1" "RANKED_SOLO_5x5" "CHALLENGER"')
