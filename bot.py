import requests
import os
from time import sleep
from datetime import datetime, timezone, timedelta
import psycopg2
import json
import threading

connections = []

class BotHandler:

    def __init__(self, token):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)
        self.keyboardLayout = json.dumps({'keyboard': [['Score'], ['Fixtures'], ['Subscribe'], ['Unsubscribe']]})


    def get_updates(self, offset=None, timeout=30):
        method = 'getUpdates'
        params = {'timeout': timeout, 'offset': offset}
        resp = requests.get(self.api_url + method, params)
        result_json = resp.json()['result']
        return result_json

    def send_message(self, chat_id, text):
        params = {'chat_id': chat_id, 'text': text, 'reply_markup': self.keyboardLayout}
        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params)
        return resp

    def get_last_update(self, offset=None):
        get_result = self.get_updates(offset)
        if len(get_result) <= 0:
            return -1
        else:
            last_update = get_result[len(get_result)-1]
            return last_update

class Barca:

    def __init__(self, token):
        self.token = token
        self.api_url = 'http://api.football-data.org/v2/'

    def fetch_fixtures(self, df, dt):
        url_extend = 'teams/81/matches'
        headers = {'X-Auth-Token': self.token}
        df = df.strftime('%Y-%m-%d')
        dt = dt.strftime('%Y-%m-%d')
        params = {'dateFrom': df, 'dateTo': dt}
        resp = requests.get(self.api_url + url_extend, headers=headers, params=params)
        resp = resp.text
        return resp

pwd = os.path.dirname(os.path.abspath(__file__))
tok = open("{}/../tok.txt".format(pwd), "r")
data = tok.readlines()
tok.close()
token1 = data[0].strip()
token2 = data[1].strip()
barca_bot = BotHandler(token1)  
data_bot = Barca(token2)

DATABASE_URL = os.environ['DATABASE_URL']

codes = {2014: 'LaLiga', 2001: 'Champions League', 2018: 'European Championship'}

def fixtures_async():

    conn1 = psycopg2.connect(DATABASE_URL, sslmode='require')
    db = conn1.cursor()
    connections.append(conn1)

    while True:
        try:
            fixtures = data_bot.fetch_fixtures(datetime.now()-timedelta(days=7), datetime.now()+timedelta(days=1))
            db.execute("UPDATE fixtures SET score=%s", (fixtures,))
            fixtures = data_bot.fetch_fixtures(datetime.now(), datetime.now()+timedelta(days=14))
            db.execute("UPDATE fixtures SET matches=%s", (fixtures,))
            fixtures = data_bot.fetch_fixtures(datetime.now()-timedelta(days=2), datetime.now()+timedelta(days=1))
            db.execute("UPDATE fixtures SET update_reminder=%s", (fixtures,))
            conn1.commit()
            sleep(21)
        except (KeyboardInterrupt, SystemExit, Exception) as e:
            print(e)
    
    db.close()
    conn1.close()

def get_fixtures(col,cur):

    cur.execute("SELECT * from fixtures")
    fixtures = cur.fetchone()
    return fixtures[col]['matches']

def score(last_chat_id, db):

    fixtures = get_fixtures(0, db)
    text = ''

    for fixture in reversed(fixtures):
        if (fixture['status'] == 'IN_PLAY' or fixture['status'] == 'PAUSED') and fixture['competition']['id'] in codes:
            text = text + '{}\n'.format(codes[fixture['competition']['id']])
            text = text + '{} VS {}\n'.format(fixture['homeTeam']['name'], fixture['awayTeam']['name'])
            text = text + '[IN PROGRESS]\n'
            penalty_home = ''
            penalty_away = ''
            if fixture['score']['penalties']['homeTeam'] is not None:
                penalty_home = '({})'.format(fixture['score']['penalties']['homeTeam'])
                penalty_away = '({})'.format(fixture['score']['penalties']['awayTeam'])
            text = text + '{}{} - {}{}'.format(fixture['score']['fullTime']['homeTeam'], penalty_home, fixture['score']['fullTime']['awayTeam'], penalty_away)
            break

    if text == '':
        for fixture in reversed(fixtures):
            if fixture['status'] == 'FINISHED' and fixture['competition']['id'] in codes:
                text = text + '{}\n'.format(codes[fixture['competition']['id']])
                text = text + '{} VS {}\n'.format(fixture['homeTeam']['name'], fixture['awayTeam']['name'])
                time = datetime.strptime(fixture['utcDate'], '%Y-%m-%dT%H:%M:%SZ')
                time = time.replace(tzinfo=timezone.utc).astimezone(tz=None)
                text = text + time.strftime('%a, %d %b\n')
                text = text + '[FINISHED]\n'
                penalty_home = ''
                penalty_away = ''
                if fixture['score']['penalties']['homeTeam'] is not None:
                    penalty_home = '({})'.format(fixture['score']['penalties']['homeTeam'])
                    penalty_away = '({})'.format(fixture['score']['penalties']['awayTeam'])
                text = text + '{}{} - {}{}'.format(fixture['score']['fullTime']['homeTeam'], penalty_home, fixture['score']['fullTime']['awayTeam'], penalty_away)
                break

    if text == '':
        text = 'No Recent Matches!'
        
    barca_bot.send_message(last_chat_id, text)

def fixtures(last_chat_id, db):

    fixtures = get_fixtures(1, db)
    count = 0
    text = ''

    for fixture in fixtures:
        if count > 4:
            break
        if fixture['status'] == 'SCHEDULED' and fixture['competition']['id'] in codes:
            text = text + '{}\n'.format(codes[fixture['competition']['id']])
            text = text + '{} VS {}\n'.format(fixture['homeTeam']['name'], fixture['awayTeam']['name'])
            time = datetime.strptime(fixture['utcDate'], '%Y-%m-%dT%H:%M:%SZ')
            time = time.replace(tzinfo=timezone.utc).astimezone(tz=timezone(timedelta(hours=5, minutes=30)))
            text = text + time.strftime('%a, %d %b\n%I:%M %p')
            text = text + '\n\n'
            count += 1

    if text == '':
        text = 'No Upcoming Matches!'

    barca_bot.send_message(last_chat_id, text)

def subscribe(last_chat_id, last_chat_name, isGroup, conn, db):

    text = ''
    db.execute("SELECT * FROM subscribers WHERE id = %s", (last_chat_id,))
    rows = db.fetchall()
    if len(rows) == 0:
        db.execute("INSERT INTO subscribers(id) VALUES(%s)", (last_chat_id,))
        conn.commit()
        if isGroup == False:
            text = 'Cheers {}! You are now subscribed for automatic updates and reminders! Forca Barca!'.format(last_chat_name)
        else:
            text = 'Cheers! This group is now subscribed for automatic updates and reminders! Forca Barca!'
    else:
        if isGroup == False:
            text = '{}, you are already Subscribed'.format(last_chat_name)
        else:
            text = 'This group is already Subscribed'

    barca_bot.send_message(last_chat_id, text)

def unsubscribe(last_chat_id, last_chat_name, isGroup, conn, db):

    text = ''
    db.execute("SELECT * FROM subscribers WHERE id = %s", (last_chat_id,))
    rows = db.fetchall()
    if len(rows) != 0:
        db.execute("DELETE FROM subscribers WHERE id = %s", (last_chat_id,))
        conn.commit()
        if isGroup == False:
            text = '{}, you are now unsubscribed from automatic updates and reminders! You will be missed!'.format(last_chat_name)
        else:
            text = 'This group is now unsubscribed from automatic updates and reminders! You will be missed!'
    else:
        if isGroup == False:
            text = '{}, you are already Unsubscribed'.format(last_chat_name)
        else:
            text = 'This group is already Unsubscribed'

    barca_bot.send_message(last_chat_id, text)
    
def chat():  

    conn2 = psycopg2.connect(DATABASE_URL, sslmode='require')
    db = conn2.cursor()
    connections.append(conn2)

    new_offset = None

    while True:
        try:
            flag = True
            isGroup = False
            last_update = barca_bot.get_last_update(new_offset)
            if last_update == -1:
                flag = False
            if flag == True:    
                last_update_id = last_update['update_id']
                last_chat_text = last_update['message']['text']
                last_chat_id = last_update['message']['chat']['id']
                try:
                    last_chat_name = last_update['message']['chat']['first_name']
                except:
                    isGroup = True

                # score response
                if last_chat_text.lower() == 'score' or last_chat_text.lower() == '/score':
                    score(last_chat_id, db)

                # fixtures response
                elif last_chat_text.lower() == 'fixtures' or last_chat_text.lower() == '/fixtures':
                    fixtures(last_chat_id, db)

                # subscribe action
                elif last_chat_text.lower() == 'subscribe' or last_chat_text.lower() == '/subscribe':
                    subscribe(last_chat_id, last_chat_name, isGroup, conn2, db)

                # unsubscribe action
                elif last_chat_text.lower() == 'unsubscribe' or last_chat_text.lower() == '/unsubscribe':
                    unsubscribe(last_chat_id, last_chat_name, isGroup, conn2, db)
                
                # start action
                elif last_chat_text.lower() == 'start' or last_chat_text.lower() == '/start':
                    barca_bot.send_message(last_chat_id, "Welcome to BarcaBot!")

                new_offset = last_update_id + 1
        except (KeyboardInterrupt, SystemExit, Exception) as e:
            print(e)
    
    db.close()
    conn2.close()

def send_updates_reminder():

    conn3 = psycopg2.connect(DATABASE_URL, sslmode='require')
    db = conn3.cursor()
    connections.append(conn3)

    last_notif = datetime.strptime('2017-04-14T14:15:00Z', '%Y-%m-%dT%H:%M:%SZ')

    while True:
        try:
            fixtures = get_fixtures(2, db)
            #goal updates
            text = ''
            for fixture in fixtures:
                if (fixture['status'] == 'IN_PLAY' or fixture['status'] == 'PAUSED') and fixture['competition']['id'] in codes:
                    goals = db.execute("SELECT * from scores")
                    last_home_goal = goals[0][0]
                    last_away_goal = goals[0][1]
                    if fixture['score']['fullTime']['homeTeam'] == last_home_goal and fixture['score']['fullTime']['awayTeam'] == last_away_goal:
                        break
                    text = text + '{}\n'.format(codes[fixture['competition']['id']])
                    text = text + '{} VS {}\n'.format(fixture['homeTeam']['name'], fixture['awayTeam']['name'])
                    text = text + '[IN PROGRESS]\n'
                    penalty_home = ''
                    penalty_away = ''
                    if fixture['score']['penalties']['homeTeam'] is not None:
                        penalty_home = '({})'.format(fixture['score']['penalties']['homeTeam'])
                        penalty_away = '({})'.format(fixture['score']['penalties']['awayTeam'])
                    text = text + '{}{} - {}{}'.format(fixture['score']['fullTime']['homeTeam'], penalty_home, fixture['score']['fullTime']['awayTeam'], penalty_away)
                    break
                else:
                    db.execute("UPDATE scores SET last_home_goal=0, last_away_goal=0")
                    sleep(20)

            if text != '':
                text = 'Score Update:\n\n' + text
                db.execute("SELECT * FROM subscribers")
                rows = db.fetchall()
                for row in rows:
                    barca_bot.send_message(int(row[0]), text)
                last_home_goal = fixture['score']['fullTime']['homeTeam']
                last_away_goal = fixture['score']['fullTime']['awayTeam']
                db.execute("UPDATE scores SET last_home_goal=%s, last_away_goal=%s", (last_home_goal, last_away_goal))
            
            # match reminder
            text = ''
            diff = datetime.now() - last_notif
            if diff.total_seconds() > 130000:
                for fixture in fixtures:
                    if fixture['status'] == 'SCHEDULED' and fixture['competition']['id'] in codes:
                        time = datetime.strptime(fixture['utcDate'], '%Y-%m-%dT%H:%M:%SZ')
                        diff = time - datetime.now()
                        if diff.total_seconds() > 900:
                            break
                        text = text + '{}\n'.format(codes[fixture['competition']['id']])
                        text = text + '{} VS {}\n'.format(fixture['homeTeam']['name'], fixture['awayTeam']['name'])
                        time = time.replace(tzinfo=timezone.utc).astimezone(tz=timezone(timedelta(hours=5, minutes=30)))
                        text = text + time.strftime('%a, %d %b\n%I:%M %p')
                        text = text + '\n\n'
                        break

                if text != '':
                    text = 'Reminder: Match starts in 15 minutes!\n\n' + text
                    db.execute("SELECT * FROM subscribers")
                    rows = db.fetchall()
                    for row in rows:
                        barca_bot.send_message(int(row[0]), text)
                    last_notif = datetime.now()
        except (KeyboardInterrupt, SystemExit, Exception) as e:
            print(e)
    
    db.close()
    conn3.close()

if __name__ == '__main__':  
    try:
        threads = []
        threads.append(threading.Thread(target=fixtures_async))
        threads.append(threading.Thread(target=chat))
        threads.append(threading.Thread(target=send_updates_reminder))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except (KeyboardInterrupt, SystemExit, Exception) as e:
        print(e)
        for conn in connections:
            conn.close()