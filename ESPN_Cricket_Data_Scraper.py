# Import all required libraries 
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import sys
import os
import argparse
import logging
import datetime
from logging.handlers import RotatingFileHandler
 
# Make DB connection
def get_db_conn(dbname):
    '''Returns sqlite db connection'''
    try:
        conn = sqlite3.connect(dbname+'.sqlite')
    except Exception as e:
        print('Unable to establish connection with database with error', e)
        sys.exit(-1)

    return conn


def get_country_details(country_links, selected_countries, sqlite_conn):

    cur = sqlite_conn.cursor()
    for country_link in country_links:
        country_name = re.match(
            r".*/([a-z-]+)", country_link.get('href')).group(1)
        if country_name in selected_countries:
            country = country_link.text
            # print(country)
            country_id = re.match(
                r".*/id/([0-9]+)", country_link.get('href')).group(1)
            cur.execute(
                'INSERT OR IGNORE INTO Countries (country_id,country) VALUES (?,?)', (country_id, country_name))
        else:
            continue
    sqlite_conn.commit()


def get_player_details(country_ids, sqlite_conn, match_types):

    cur = sqlite_conn.cursor()
    # print(country_ids)
    for cid, name in country_ids:
        # http://www.espncricinfo.com/australia/content/player/country.html?country=2
        # http://www.espncricinfo.com/australia/content/player/caps.html?country=2;class=3
        for type_no in match_types:
            squad_url = 'http://www.espncricinfo.com/' + \
                str(name)+'/content/player/caps.html?country=' + \
                str(cid)+';class='+str(type_no)

            squad_page = requests.get(squad_url)
            soup1 = BeautifulSoup(squad_page.text, "html.parser")
            player_links = soup1.findAll(
                'a', href=re.compile('/content/player/\d+'))
            # print(player_links)

            for i in player_links:
                if i.text:
                    player_id = i.get('href').split('/')[-1].split('.')[0]
                    # print(player_id)
                    player = i.text.strip()
                    # print(player)

                    #curs.execute("INSERT INTO items (X, Y) VALUES (:X, :Y)", {X: X, Y: Y})

                    if type_no == 2:

                        cur.execute('INSERT OR IGNORE INTO Players (country_id,player_id,player) VALUES (:X, :Y, :Z)', {
                                    'X': cid, 'Y': player_id, 'Z': player})
                        # If new entry comes in just get updated
                        cur.execute("UPDATE Players Set odi_cap ='Y' where country_id=:X AND player_id=:Y AND player=:Z", {
                                    'X': cid, 'Y': player_id, 'Z': player})

                    elif type_no == 3:

                        cur.execute('INSERT OR IGNORE INTO Players (country_id,player_id,player) VALUES (:X, :Y, :Z)', {
                                    'X': cid, 'Y': player_id, 'Z': player})
                        cur.execute("UPDATE Players Set t20_cap ='Y' where country_id=:X AND player_id=:Y AND player=:Z", {
                                    'X': cid, 'Y': player_id, 'Z': player})

                sqlite_conn.commit()


def get_player_statistics(action, play_list, match_type, sqlite_conn):

    cur = sqlite_conn.cursor()
    i = 0
    # print(play_list)
    print('match_type>>>', match_type)
    for play in play_list:
        i += 1
        if i % 100 == 0:
            print('completed', i)
        pid = play[2]
        country_name = play[1]
        player_name = play[3]

        # http://stats.espncricinfo.com/ci/engine/player/4558.html?class=3;template=results;type=batting;view=innings
        stats_url = 'http://stats.espncricinfo.com/ci/engine/player/' + \
            str(pid)+'.html?class='+str(match_type) + \
            ';template=results;type='+str(action)+';view=innings'
        try:
            stats_page = requests.get(stats_url)
            soup2 = BeautifulSoup(stats_page.text, "html.parser")
            print(stats_url)
            print(soup2.prettify())
            print(">>>>>>>>>>>>>>>>>>>>>>>>\n")
            print(soup2.findAll('tr',{"class": "head"}))
            cols_tag = soup2.findAll('tr', {"class": "head"})[0].findAll("th")
            vals_tag = soup2.findAll("tr", {"class": "data1"})[0].findAll('td')

            cols = [cols_tag[i].get_text() for i in range(1, len(cols_tag)-1)]
            vals = [vals_tag[i].get_text() for i in range(1, len(vals_tag)-1)]

            dict_col_val = dict(zip(cols, vals))
            # print(dict_col_val)
        except Exception as e:
            print('Exception error for below player:', e)
            continue

        if match_type == 2:
            table_name_bat = 'Batting_Stats_Odi'
            table_name_bowl = 'Bowling_Stats_Odi'
        elif match_type == 3:
            table_name_bat = 'Batting_Stats_T20'
            table_name_bowl = 'Bowling_Stats_T20'

        if action == "bowling":

            Span = dict_col_val.get('Span', 'NA')
            Mat = dict_col_val.get('Mat', 'NA')
            Inns = dict_col_val.get('Inns', 'NA')
            Overs = dict_col_val.get('Overs', 'NA')
            Balls = dict_col_val.get('Balls', 'NA')
            Runs = dict_col_val.get('Runs', 'NA')
            Mdns = dict_col_val.get('Mdns', 'NA')
            Wkts = dict_col_val.get('Wkts', 'NA')
            BBI = dict_col_val.get('BBI', 'NA')
            Ave = dict_col_val.get('Ave', 'NA')
            Econ = dict_col_val.get('Econ', 'NA')
            SR = dict_col_val.get('SR', 'NA')
            fourW = dict_col_val.get('4', 'NA')
            fiveW = dict_col_val.get('5', 'NA')

            cur.execute('''INSERT OR IGNORE INTO '''+table_name_bowl + '''  (player,playing_span ,matches_played,innings_bowled_in,
                    overs_bowled ,balls_bowled ,runs_conceded ,maidens_earned ,wickets_taken , 
                    best_bowling_in_an_innings ,bowling_average ,economy_rate ,bowling_strike_rate ,
                    four_wkts_exactly_in_an_inns ,five_wickets_in_an_inns)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (player_name, Span, Mat, Inns, Overs, Balls, Runs, Mdns, Wkts, BBI, Ave, Econ, SR, fourW, fiveW))
            sqlite_conn.commit()

        elif action == 'batting':

            Span = dict_col_val.get('Span', 'NA')
            Mat = dict_col_val.get('Mat', 'NA')
            Inns = dict_col_val.get('Inns', 'NA')
            NO = dict_col_val.get('NO', 'NA')
            Runs = dict_col_val.get('Runs', 'NA')
            HS = dict_col_val.get('HS', 'NA')
            Ave = dict_col_val.get('Ave', 'NA')
            BF = dict_col_val.get('BF', 'NA')
            SR = dict_col_val.get('SR', 'NA')
            No100s = dict_col_val.get('100', 'NA')
            No50s = dict_col_val.get('50', 'NA')
            Ducks = dict_col_val.get('0', 'NA')
            Fours = dict_col_val.get('4s', 'NA')
            Sixes = dict_col_val.get('6s', 'NA')

            cur.execute('''INSERT OR IGNORE INTO '''+table_name_bat+''' (player,playing_span ,matches_played ,
                    innings_batted ,not_outs, runs_scored ,highest_innings_score ,batting_average ,
                    balls_faced ,batting_strike_rate ,hundreds_scored ,scores_between_50_and_99 ,ducks_scored ,
                    boundary_fours ,boundary_sixes)VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (player_name, Span, Mat, Inns, NO, Runs, HS, Ave, BF, SR, No100s, No50s, Ducks, Fours, Sixes))
            sqlite_conn.commit()


# Driver function runs from here
def main():

    global url
    global year
    global dbname
    global match_type
    # Setup logger

    logger = logging.getLogger(__name__)

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = RotatingFileHandler(
        'espn_cricket_data_scraper.log', maxBytes=10485760, backupCount=20)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.info("Process Start at {}".format(str(datetime.datetime.now())))

    #[australia,bangladesh,england,india,new-zealand,pakistan,south-africa,sri-lanka,west-indies,zimbabwe,afghanistan]
    # Argument parser
    parser = argparse.ArgumentParser(
        description='Cricket Performance Data Parser')

    parser.add_argument('-d', '--databasename', dest='databasename', default='DEFAULT_DB',
                        help='Sqlite Master Database name to store the details')
    parser.add_argument('-t', '--typeofmatch', dest='typeofmatch', default='ALL',
                        help='enter ODI/T20/ALL to fetch corresponding data')
    parser.add_argument('-c', '--countries', dest='countries', default='ALL', nargs='*',
                        help='valid entries =  [australia,bangladesh,england,india,new-zealand,pakistan,south-africa,sri-lanka,west-indies,zimbabwe,afghanistan].Players performance from mentioned countries data would be updated in database,default = ALL to update all players from all countries')

    args = parser.parse_args()
    dbname = args.databasename
    countries = args.countries
    match_type = args.typeofmatch

    all_countries = ['australia', 'bangladesh', 'england', 'india', 'new-zealand',
                     'pakistan', 'south-africa', 'sri-lanka', 'west-indies', 'zimbabwe', 'afghanistan']

    if countries == 'ALL':
        selected_countries = all_countries
    else:
        selected_countries = [x for x in countries if x in all_countries]

    #u1 = 'http://www.espncricinfo.com/story/_/id/18791072/all-cricket-teams-index'
    # http://www.espncricinfo.com/team/_/id/7/pakistan/
    #U1 = 'http://stats.espncricinfo.com/ci/engine/player/348144.html?class=3;template=results;type=batting;view=innings;year=2018'

    # main cricket teams web page url
    # url='http://www.espncricinfo.com/icc-cricket-world-cup-2015/content/current/series/509587.html'

    # This is the final useable links to get country_id 
    url = 'http://www.espncricinfo.com/story/_/id/18791072/all-cricket-teams-index'
    page = requests.get(url)

    # Check if webpage is active
    if page.status_code == 200:
        logger.info(
            'Url status code indicates active status,proceeding with webscraping')

    elif page.status_code == 404:
        logger.error("Url provided doesn't exist,exiting with error code 404")
        sys.exit(-1)

    # creating BeautifulSoup Object
    soup = BeautifulSoup(page.text, "html.parser")

    country_links = soup.find_all('a', href=re.compile('/team/_/id/'))

    # print(soup.prettify())
    # display(HTML(page.text))
    # print(country_links)

    # Create all necessary tables in database for insertion of stats data
    with get_db_conn(dbname) as sqlite_conn:
        cur = sqlite_conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS Countries
                (country_id INTEGER PRIMARY KEY,country TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS Players
                (country_id INTEGER,player_id INTEGER UNIQUE,player TEXT,odi_cap TEXT,t20_cap TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS Batting_Stats_Odi (player TEXT,playing_span TEXT,matches_played TEXT,
                    innings_batted TEXT,not_outs TEXT, runs_scored TEXT,highest_innings_score TEXT,batting_average TEXT,
                    balls_faced TEXT,batting_strike_rate TEXT,hundreds_scored TEXT,scores_between_50_and_99 TEXT,
                    ducks_scored TEXT,boundary_fours TEXT,boundary_sixes TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS Bowling_Stats_Odi (player TEXT,playing_span TEXT,matches_played TEXT,innings_bowled_in TEXT,
                    overs_bowled TEXT,balls_bowled TEXT,runs_conceded TEXT,maidens_earned TEXT,wickets_taken TEXT, 
                    best_bowling_in_an_innings TEXT,bowling_average TEXT,economy_rate TEXT,bowling_strike_rate TEXT,
                    four_wkts_exactly_in_an_inns TEXT,five_wickets_in_an_inns TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS Batting_Stats_T20 (player TEXT,playing_span TEXT,matches_played TEXT,
                    innings_batted TEXT,not_outs TEXT, runs_scored TEXT,highest_innings_score TEXT,batting_average TEXT,
                    balls_faced TEXT,batting_strike_rate TEXT,hundreds_scored TEXT,scores_between_50_and_99 TEXT,ducks_scored TEXT,
                    boundary_fours TEXT,boundary_sixes TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS Bowling_Stats_T20 (player TEXT, playing_span TEXT,matches_played TEXT,innings_bowled_in TEXT,
                    overs_bowled TEXT,balls_bowled TEXT,runs_conceded TEXT,maidens_earned TEXT,wickets_taken TEXT, 
                    best_bowling_in_an_innings TEXT,bowling_average TEXT,economy_rate TEXT,bowling_strike_rate TEXT,
                    four_wkts_exactly_in_an_inns TEXT,five_wickets_in_an_inns TEXT)''')

        sqlite_conn.commit()

    logger.info('Created necessary tables in database')

    # Fetch all  countires name and id and store in database
    with get_db_conn(dbname) as sqlite_conn:
        logger.info('Fetching select countries data')
        get_country_details(country_links, selected_countries, sqlite_conn)

    logger.info('Inserted data into Countries table')
    # print('Inserted data into Countries table')

    # Fetch countries id from database and store in list
    with get_db_conn(dbname) as sqlite_conn:
        cur = sqlite_conn.cursor()
        cur.execute('SELECT country_id,country FROM Countries')
        countryid_list = list()
        for row in cur:
            countryid_list.append(row)

        # Now it's time to store data in  players table
        if match_type == 'ODI':
            get_player_details(countryid_list, sqlite_conn, [2])
        elif match_type == 'T20':
            get_player_details(countryid_list, sqlite_conn, [3])
        elif match_type == 'ALL':
            get_player_details(countryid_list, sqlite_conn, [2, 3])

    logger.info('Inserted data into Players table')
    print('Inserted data into Players table')

    # select country id,name and player id,name from database and fetch player statistics
    with get_db_conn(dbname) as sqlite_conn:
        cur = sqlite_conn.cursor()

        cur.execute(
            '''select a.country_id,a.country,b.player_id,b.player from Countries a,Players b where a.country_id=b.country_id and b.odi_cap="Y";''')
        play_listodi = list()
        for row in cur:
            play_listodi.append(row)

        cur.execute(
            '''select a.country_id,a.country,b.player_id,b.player from Countries a,Players b where a.country_id=b.country_id and b.t20_cap="Y";''')
        play_listt20 = list()
        for row in cur:
            play_listt20.append(row)
############################################################################################################

    with get_db_conn(dbname) as sqlite_conn:

        if match_type == 'ODI':
            for action in ['batting', 'bowling']:
                get_player_statistics(action, play_listodi, 2, sqlite_conn)

        elif match_type == 'T20':
            for action in ['batting', 'bowling']:
                get_player_statistics(action, play_listt20, 3, sqlite_conn)

        elif match_type == 'ALL':
            for action in ['batting', 'bowling']:
                get_player_statistics(action, play_listodi, 2, sqlite_conn)
                get_player_statistics(action, play_listt20, 3, sqlite_conn)

    logger.info(
        'Successfully collected Player bowling and batting statistics and stored in database')
    print('Successfully collected Player bowling and batting statistics and stored in database')


if __name__ == "__main__":
    main()
