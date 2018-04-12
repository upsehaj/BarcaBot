import requests
import os

class BotHandler:

    def __init__(self, token):
        self.token = token
        self.api_url = 'https://api.telegram.org/bot{}/'.format(token)

    def get_updates(self, offset=None, timeout=60):
        method = 'getUpdates'
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

    def get_last_update(self):
        get_result = self.get_updates()
        if len(get_result) <= 0:
            last_update = -1
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
        params = {'timeFrame': 'n7'}
        resp = requests.get(self.api_url + url_extend, headers=headers)
        result_json = resp.json()['fixtures']
        return result_json

    

pwd = os.path.dirname(os.path.abspath(__file__))
tok = open("{}/../tok.txt".format(pwd), "r")
data = tok.readlines()
token1 = data[0]
token2 = data[1]
barca_bot = BotHandler(token1)  
data_bot = Barca(token2)

def main():  

    new_offset = None

    while True:
        barca_bot.get_updates(new_offset)
        last_update = barca_bot.get_last_update()
        if last_update == -1:
            continue
        last_update_id = last_update['update_id']
        last_chat_text = last_update['message']['text']
        last_chat_id = last_update['message']['chat']['id']
        last_chat_name = last_update['message']['chat']['first_name']

        

        if last_chat_text.lower() == 'score':
            text = 'Scores Feature is still under development. Sorry for inconvenience'
            barca_bot.send_message(last_chat_id, text)
        elif last_chat_text.lower() == 'fix':
            text = 'Fixtures Feature is still under development. Sorry for inconvenience'
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