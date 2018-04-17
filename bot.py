import requests
import os
from time import sleep
from datetime import datetime, timezone, timedelta
import sqlite3

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
        self.api_url = 'http://api.football-data.org/v1/'

    def get_fix(self, days):
        url_extend = 'teams/81/fixtures'
        headers = {'X-Response-Control': 'minified', 'X-Auth-Token': self.token}
        params = {'timeFrame': days}
        resp = requests.get(self.api_url + url_extend, headers=headers, params=params)
        result_json = resp.json()['fixtures']
        return result_json

pwd = os.path.dirname(os.path.abspath(__file__))
tok = open("{}/../tok.txt".format(pwd), "r")
data = tok.readlines()
tok.close()
token1 = data[0].strip()
token2 = data[1].strip()
barca_bot = BotHandler(token1)  
data_bot = Barca(token2)

conn = sqlite3.connect('subscription.db')
db = conn.cursor()

def main():  

    new_offset = None
    codes = {455: 'LaLiga', 464: 'Champions League', 446: 'UEFA Cup'}
    last_notif = datetime.strptime('2017-04-14T14:15:00Z', '%Y-%m-%dT%H:%M:%SZ')
    # last_sc = datetime.now()
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
                fixtures = data_bot.get_fix('n2')
                text = ''
                for fixture in fixtures:
                    if fixture['status'] == 'IN_PLAY' and fixture['competitionId'] in codes:
                        text = text + '{}\n'.format(codes[fixture['competitionId']])
                        text = text + '{} VS {}\n'.format(fixture['homeTeamName'], fixture['awayTeamName'])
                        text = text + '[IN PROGRESS]\n'
                        penalty_home = ''
                        penalty_away = ''
                        if 'penaltyShootout' in fixture:
                            penalty_home = '({})'.format(fixture['result']['penaltyShootout']['goalsHomeTeam'])
                            penalty_away = '({})'.format(fixture['result']['penaltyShootout']['goalsAwayTeam'])
                        text = text + '{}{} - {}{}'.format(fixture['result']['goalsHomeTeam'], penalty_home, fixture['result']['goalsAwayTeam'], penalty_away)
                        break

                    if text == '':
                        fixtures = data_bot.get_fix('p2')
                        for fixture in reversed(fixtures):
                            if fixture['status'] == 'FINISHED' and fixture['competitionId'] in codes:
                                text = text + '{}\n'.format(codes[fixture['competitionId']])
                                text = text + '{} VS {}\n'.format(fixture['homeTeamName'], fixture['awayTeamName'])
                                time = datetime.strptime(fixture['date'], '%Y-%m-%dT%H:%M:%SZ')
                                time = time.replace(tzinfo=timezone.utc).astimezone(tz=None)
                                text = text + time.strftime('%a, %d %b\n')
                                text = text + '[FINISHED]\n'
                                penalty_home = ''
                                penalty_away = ''
                                if 'penaltyShootout' in fixture:
                                    penalty_home = '({})'.format(fixture['result']['penaltyShootout']['goalsHomeTeam'])
                                    penalty_away = '({})'.format(fixture['result']['penaltyShootout']['goalsAwayTeam'])
                                text = text + '{}{} - {}{}'.format(fixture['result']['goalsHomeTeam'], penalty_home, fixture['result']['goalsAwayTeam'], penalty_away)
                                break
                if text == '':
                    text = 'No Recent Matches!'
                barca_bot.send_message(last_chat_id, text)
                new_offset = last_update_id + 1

            # fixtures response
            elif last_chat_text.lower() == 'fix' or last_chat_text.lower() == '/fix':
                fixtures = data_bot.get_fix('n14')
                count = 0
                text = ''
                for fixture in fixtures:
                    if count > 4:
                        break
                    if fixture['status'] == 'TIMED' and fixture['competitionId'] in codes:
                        text = text + '{}\n'.format(codes[fixture['competitionId']])
                        text = text + '{} VS {}\n'.format(fixture['homeTeamName'], fixture['awayTeamName'])
                        time = datetime.strptime(fixture['date'], '%Y-%m-%dT%H:%M:%SZ')
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
                db.execute("SELECT * FROM subscribers WHERE id = ?", (last_chat_id,))
                rows = db.fetchall()
                if len(rows) == 0:
                    db.execute("INSERT INTO subscribers(id) VALUES(?)", (last_chat_id,))
                    conn.commit()
                    if isGroup == False:
                        text = 'Congratulations {}! You are now subscribed for automatic updates! Forca Barca!'.format(last_chat_name)
                    else:
                        text = 'Congratulations! This group is now subscribed for automatic updates! Forca Barca!'
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
                db.execute("SELECT * FROM subscribers WHERE id = ?", (last_chat_id,))
                rows = db.fetchall()
                if len(rows) != 0:
                    db.execute("DELETE FROM subscribers WHERE id = ?", (last_chat_id,))
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

        
        fixtures = data_bot.get_fix('n2')

        # goal update
        text = ''
        for fixture in fixtures:
            if fixture['status'] == 'IN_PLAY' and fixture['competitionId'] in codes:
                if fixture['result']['goalsHomeTeam'] == last_home_goal and fixture['result']['goalsAwayTeam'] == last_away_goal:
                    break
                last_home_goal = fixture['result']['goalsHomeTeam']
                last_away_goal = fixture['result']['goalsAwayTeam']
                text = text + '{}\n'.format(codes[fixture['competitionId']])
                text = text + '{} VS {}\n'.format(fixture['homeTeamName'], fixture['awayTeamName'])
                text = text + '[IN PROGRESS]\n'
                penalty_home = ''
                penalty_away = ''
                if 'penaltyShootout' in fixture:
                    penalty_home = '({})'.format(fixture['result']['penaltyShootout']['goalsHomeTeam'])
                    penalty_away = '({})'.format(fixture['result']['penaltyShootout']['goalsAwayTeam'])
                text = text + '{}{} - {}{}'.format(fixture['result']['goalsHomeTeam'], penalty_home, fixture['result']['goalsAwayTeam'], penalty_away)
                break
            elif fixture['status'] != 'IN_PLAY' and fixture['competitionId'] in codes:
                last_home_goal = 0
                last_away_goal = 0

        if text != '':
            text = 'Score Update:\n\n' + text
            db.execute("SELECT * FROM subscribers")
            rows = db.fetchall()
            for row in rows:
                barca_bot.send_message(int(row[0]), text)

        # score update
        # text = ''
        # diff = datetime.now() - last_sc
        # if diff.total_seconds() >= 899:
        #     text = ''
        #     for fixture in fixtures:
        #         if fixture['status'] == 'IN_PLAY' and fixture['competitionId'] in codes:
        #             text = text + '{}\n'.format(codes[fixture['competitionId']])
        #             text = text + '{} VS {}\n'.format(fixture['homeTeamName'], fixture['awayTeamName'])
        #             text = text + '[IN PROGRESS]\n'
        #             penalty_home = ''
        #             penalty_away = ''
        #             if 'penaltyShootout' in fixture:
        #                 penalty_home = '({})'.format(fixture['result']['penaltyShootout']['goalsHomeTeam'])
        #                 penalty_away = '({})'.format(fixture['result']['penaltyShootout']['goalsAwayTeam'])
        #             text = text + '{}{} - {}{}'.format(fixture['result']['goalsHomeTeam'], penalty_home, fixture['result']['goalsAwayTeam'], penalty_away)
        #             last_sc = datetime.now()
        #             break
        #     if text != '':
        #         text = 'Score Update:\n\n' + text
        #         for person in subscription:
        #             barca_bot.send_message(person, text)

            # match reminder
            text = ''
            diff = datetime.now() - last_notif
            if diff.total_seconds() > 40000:
                for fixture in fixtures:
                    if fixture['status'] == 'TIMED' and fixture['competitionId'] in codes:
                        time = datetime.strptime(fixture['date'], '%Y-%m-%dT%H:%M:%SZ')
                        diff = time - datetime.now()
                        if diff.total_seconds() > 300:
                            break
                        last_notif = datetime.now()
                        text = text + '{}\n'.format(codes[fixture['competitionId']])
                        text = text + '{} VS {}\n'.format(fixture['homeTeamName'], fixture['awayTeamName'])
                        time = time.replace(tzinfo=timezone.utc).astimezone(tz=None)
                        text = text + time.strftime('%a, %d %b\n%I:%M %p')
                        text = text + '\n\n'
                        break
                if text != '':
                    text = 'Reminder: Match starts in 5 minutes!\n\n' + text
                    db.execute("SELECT * FROM subscribers")
                    rows = db.fetchall()
                    for row in rows:
                        barca_bot.send_message(int(row[0]), text)

if __name__ == '__main__':  
    try:
        main()
    except (KeyboardInterrupt, SystemExit, SystemExit, Exception) as e:
        print(e)
        conn.close()
        pass