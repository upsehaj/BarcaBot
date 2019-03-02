import requests
import os
from time import sleep
from datetime import datetime, timezone, timedelta
import psycopg2

class BotHandler:

    def __init__(self, token):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)

    def get_updates(self, offset=None, timeout=30):
        method = 'getUpdates'
        params = {'timeout': timeout, 'offset': offset}
        resp = requests.get(self.api_url + method, params)
        result_json = resp.json()['result']
        return result_json

    def send_message(self, chat_id, text):
        params = {'chat_id': chat_id, 'text': text}
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

    def get_fix(self, df, dt):
        url_extend = 'teams/81/matches'
        headers = {'X-Auth-Token': self.token}
        df = df.strftime('%Y-%m-%d')
        dt = dt.strftime('%Y-%m-%d')
        params = {'dateFrom': df, 'dateTo': dt}
        resp = requests.get(self.api_url + url_extend, headers=headers, params=params)
        result_json = resp.json()['matches']
        return result_json

pwd = os.path.dirname(os.path.abspath(__file__))
tok = open("{}/../tok.txt".format(pwd), "r")
data = tok.readlines()
tok.close()
token1 = data[0].strip()
token2 = data[1].strip()
barca_bot = BotHandler(token1)  
data_bot = Barca(token2)

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
db = conn.cursor()

def main():  

    new_offset = None
    codes = {2014: 'LaLiga', 2001: 'Champions League', 2018: 'European Championship'}
    last_notif = datetime.strptime('2017-04-14T14:15:00Z', '%Y-%m-%dT%H:%M:%SZ')
    last_home_goal = 0
    last_away_goal = 0
    
    while True:
        
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
                fixtures = data_bot.get_fix(datetime.now()-timedelta(days=7), datetime.now())
                text = ''
                for fixture in fixtures:
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
                        fixtures = data_bot.get_fix(datetime.now()-timedelta(days=2), datetime.now())
                        for fixture in fixtures:
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
                new_offset = last_update_id + 1

            # fixtures response
            elif last_chat_text.lower() == 'fix' or last_chat_text.lower() == '/fix':
                fixtures = data_bot.get_fix(datetime.now(), datetime.now()+timedelta(days=14))
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
                new_offset = last_update_id + 1

            # subscribe action
            elif last_chat_text.lower() == 'subscribe' or last_chat_text.lower() == '/subscribe':
                text = ''
                db.execute("SELECT * FROM subscribers WHERE id = %s", (last_chat_id,))
                rows = db.fetchall()
                if len(rows) == 0:
                    db.execute("INSERT INTO subscribers(id) VALUES(%s)", (last_chat_id,))
                    conn.commit()
                    if isGroup == False:
                        text = 'Cheers {}! You are now subscribed for automatic updates! Forca Barca!'.format(last_chat_name)
                    else:
                        text = 'Cheers! This group is now subscribed for automatic updates! Forca Barca!'
                else:
                    if isGroup == False:
                        text = '{}, you are already Subscribed'.format(last_chat_name)
                    else:
                        text = 'This group is already Subscribed'
                barca_bot.send_message(last_chat_id, text)
                new_offset = last_update_id + 1

            # unsubscribe action
            elif last_chat_text.lower() == 'unsubscribe' or last_chat_text.lower() == '/unsubscribe':
                text = ''
                db.execute("SELECT * FROM subscribers WHERE id = %s", (last_chat_id,))
                rows = db.fetchall()
                if len(rows) != 0:
                    db.execute("DELETE FROM subscribers WHERE id = %s", (last_chat_id,))
                    conn.commit()
                    if isGroup == False:
                        text = '{}, you are now unsubscribed from automatic updates! You will be missed!'.format(last_chat_name)
                    else:
                        text = 'This group is now unsubscribed from automatic updates! You will be missed!'
                else:
                    if isGroup == False:
                        text = '{}, you are already Unsubscribed'.format(last_chat_name)
                    else:
                        text = 'This group is already Unsubscribed'
                barca_bot.send_message(last_chat_id, text)
                new_offset = last_update_id + 1
            
            else:
                new_offset = last_update_id + 1
        
        fixtures = data_bot.get_fix(datetime.now()-timedelta(days=2), datetime.now())
        # goal update
        text = ''
        for fixture in fixtures:
            if (fixture['status'] == 'IN_PLAY' or fixture['status'] == 'PAUSED') and fixture['competition']['id'] in codes:
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
            elif fixture['status'] != 'IN_PLAY' and fixture['status'] != 'PAUSED' and fixture['competition']['id'] in codes:
                last_home_goal = 0
                last_away_goal = 0
                break

        if text != '':
            text = 'Score Update:\n\n' + text
            db.execute("SELECT * FROM subscribers")
            rows = db.fetchall()
            for row in rows:
                barca_bot.send_message(int(row[0]), text)
            last_home_goal = fixture['score']['fullTime']['homeTeam']
            last_away_goal = fixture['score']['fullTime']['awayTeam']

        # match reminder
        text = ''
        diff = datetime.now() - last_notif
        if diff.total_seconds() > 40000:
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

if __name__ == '__main__':  
    try:
        main()
    except (KeyboardInterrupt, SystemExit, SystemExit, Exception) as e:
        print(e)
        conn.close()