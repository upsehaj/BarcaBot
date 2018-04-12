import requests
import datetime
import os

class BotHandler:

    def __init__(self, token):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)

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

pwd = os.path.dirname(os.path.abspath(__file__))
tok = open("{}/../tok.txt".format(pwd), "r")
data = tok.readlines()
token = data[0]
barca_bot = BotHandler(token)  
now = datetime.datetime.now()

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
        # last_chat_name = last_update['message']['chat']['first_name']

        now = datetime.datetime.now()

        if last_chat_text.lower() == 'score':
            text = 'this is score'
            barca_bot.send_message(last_chat_id, text)
        elif last_chat_text.lower() == 'fix':
            text = 'this is fix'
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