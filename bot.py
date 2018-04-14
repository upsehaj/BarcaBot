import requests
import os
from datetime import datetime, timezone

class BotHandler:

    def __init__(self, token):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)

    def get_updates(self, offset=None, timeout=60):
        method = 'getUpdtes'
        params = {'timeout': timeout, 'offset': offset}
        resp = requests.get(self.api_url + method, params)
        print(resp.json())
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

    def get_fix(self):
        url_extend = 'teams/81/fixtures'
        headers = {'X-Response-Control': 'minified', 'X-Auth-Token': self.token}
        params = {'timeFrame': 'n14'}
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

def main():  

    new_offset = None
    codes = {455: 'LaLiga', }
    while True:
        last_update = barca_bot.get_last_update(new_offset)
        if last_update == -1:
            continue
        last_update_id = last_update['update_id']
        last_chat_text = last_update['message']['text']
        last_chat_id = last_update['message']['chat']['id']
        last_chat_name = last_update['message']['chat']['first_name']

        fixtures = data_bot.get_fix()

        if last_chat_text.lower() == 'score':
            text = 'Scores Feature is still under development. Sorry for the inconvenience'
            barca_bot.send_message(last_chat_id, text)
            new_offset = last_update_id + 1

        elif last_chat_text.lower() == 'fix':
            count = 0
            text = ''
            for fixture in fixtures:
                if count > 4:
                    break
                if fixture['status'] == 'TIMED':
                    text = text + '{}\n'.format(codes[fixture['competitionId']])
                    text = text + '{} v/s {}\n'.format(fixture['homeTeamName'], fixture['awayTeamName'])
                    time = datetime.strptime(fixture['date'], '%Y-%m-%dT%H:%M:%SZ')
                    time = time.replace(tzinfo=timezone.utc).astimezone(tz=None)
                    text = text + time.strftime('%a, %d %b\n%I:%M %p')
                    text = text + '\n\n'
                    count += 1

            barca_bot.send_message(last_chat_id, text)
            new_offset = last_update_id + 1

if __name__ == '__main__':  
    try:
        main()
    except KeyboardInterrupt:
        exit()
'''
score on demand
fixtures on demand
score after every 15min
score whenever a goal scored
notify a day before the match 
'''