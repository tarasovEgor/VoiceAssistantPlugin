import json
import openai
import os
import requests

from asterisk.ami import AMIClient, SimpleAction

# Класс, методы которого вызываются при перенаправлении клиетского запроса в chatGPT
# Взято из: https://github.com/janvarev/Irene-Voice-Assistant/blob/master/plugins/plugin_boltalka_vsegpt.py
class ChatApp:
    def __init__(self, model="gpt-3.5-turbo", api_key='', system=''):
        self.model = model
        self.api_key = api_key
        self.messages = []
        if system:
            self.messages.append({"role": "system", "content": system})


    def chat(self, message):
        if message == "exit":
            self.save()
            os._exit(1)
        elif message == "save":
            self.save()
            return "(saved)"
        
        self.messages.append({"role": "user", "content": message})

        openai.api_key = self.api_key
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.messages,
            temperature=0.8,
            n=1,
            max_tokens=200,
        )
        self.messages.append({"role": "assistant", "content": response["choices"][0]["message"].content})
        return response["choices"][0]["message"].content


    def save(self):
        try:
            import time
            import re
            ts = time.time()
            json_object = json.dumps(self.messages, indent=4)
            filename_prefix = self.messages[0]['content'][:30]
            filename_prefix = re.sub('[^0-9a-zA-Z]+', '-', f"{filename_prefix}_{ts}")
            with open(f"models/chat_model_{filename_prefix}.json", "w") as outfile:
                outfile.write(json_object)
        except:
            os._exit(1)


    def load(self, load_file):
        with open(load_file) as f:
            data = json.load(f)
            self.messages = data


def handle_incoming_call(event, ami_client, chat_app):
    channel = event['Channel']
    
    # Ответ на звонок
    action = SimpleAction('Answer', Channel=channel)
    ami_client.send_action(action)
    
    # Запрос ИНН пользователя (в качестве аргумента File, объекта SimpleAction указывается название .wav файла, поддерживаются и другие форматы (.gsm, .ulaw))
    ami_client.send_action(SimpleAction('Playback', Channel=channel, File='please-enter-your-inn'))
    user_inn = collect_dtmf(ami_client, channel)
    
    if verify_user_inn(user_inn):
        # При наличии ИНН в базе - запрос на описание проблемы пользователя 
        ami_client.send_action(SimpleAction('Playback', Channel=channel, File='please-describe-your-issue'))
        issue_description = collect_dtmf(ami_client, channel)

        # Передача запроса в chatGPT и сохранение ответа
        response = chat_app.chat(issue_description)
        
        # Проигрываение ответа от chatGPT пользователю
        ami_client.send_action(SimpleAction('Playback', Channel=channel, Text=response))

        # Запрос пользователю на удовлетворенность ответом
        ami_client.send_action(SimpleAction('Playback', Channel=channel, File='are-you-satisfied'))
        satisfaction_response = collect_dtmf(ami_client, channel)
    
        if satisfaction_response.lower() == 'no':
            # При запросе пользователя оставить ИНН, запросите дополнительные данные
            ami_client.send_action(SimpleAction('Playback', Channel=channel, File='please-enter-your-name'))
            user_name = collect_dtmf(ami_client, channel)
            
            ami_client.send_action(SimpleAction('Playback', Channel=channel, File='please-enter-your-phone-number'))
            phone_number = collect_dtmf(ami_client, channel)
            
            ami_client.send_action(SimpleAction('Playback', Channel=channel, File='please-describe-the-issue'))
            issue_description = collect_dtmf(ami_client, channel)
            
            ami_client.send_action(SimpleAction('Playback', Channel=channel, File='please-enter-convenient-time'))
            convenient_time = collect_dtmf(ami_client, channel)
            
            # Формирование отчета о проблеме с полученными данными
            issue_report = "User INN: {}\nUser Name: {}\nPhone Number: {}\nIssue Description: {}\nConvenient Time: {}\nChatGPT Response: {}".format(user_inn, user_name, phone_number, issue_description, convenient_time, response)
            
            # Интеграция с Zammad Helpdesk
            zammad_integration(issue_report)
    else:
        ami_client.send_action(SimpleAction('Playback', Channel=channel, File='invalid-id'))


def collect_dtmf(ami_client, channel):
    digits = ''
    while True:
        response = ami_client.send_action(SimpleAction('WaitForDigit', Channel=channel, Timeout=10000))
        digit = response.response.get('Digit')
        if digit == '#':
            break
        digits += digit
    return digits


def verify_user_inn(user_inn):
    # Проверка наличия ИНН в базе (пример)
    valid_inns = ['1234567890', '5678765432', '9012212345']
    return user_inn in valid_inns


def zammad_integration(issue_report):
    # Zammad API эндпоинт для создания новой заявки
    zammad_api_url = 'https://zammad-instance/api/v1/tickets'

    api_token = 'zammad-api-token'

    headers = {
        'Authorization': 'Token {}'.format(api_token),
        'Content-Type': 'application/json',
    }

    # Данные для отправки POST-запроса на API Zammad (https://docs.zammad.org/en/latest/api/ticket/index.html)
    data = {
        'title': 'Issue Report',
        'group': 1,  
        'customer': 1, 
        'article': {
            'subject': 'Issue Report',
            'body': issue_report,
            'type': 'note',
            'internal': 'false'
        }
    }

    try:
        # Отправка POST-запроса на создание нового тикета в Zammad
        response = requests.post(zammad_api_url, headers=headers, json=data)
        
        if response.status_code == 201:
            print("Заявка успешно создана")
        else:
            print("При создании заявки произошла ошибка. Status code:", response.status_code)
            print("Response:", response.text)
    except Exception as e:
        print("При создании заявки произошла ошибка:", str(e))


def main():
    ami_client = AMIClient(address='asterisk_server_ip', port=5038)
    ami_client.login(username='your_ami_username', secret='your_ami_secret')

    chat_app = ChatApp(api_key='your_openai_api_key')

    def on_event(event):
        if event.name == 'Newstate' and event.get('ChannelStateDesc') == 'Ringing':
            handle_incoming_call(event, ami_client, chat_app)

    ami_client.add_event_listener(on_event)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        ami_client.logoff()

if __name__ == "__main__":
    main()
