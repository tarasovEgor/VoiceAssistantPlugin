# Tech-support line automation plugin
# author: Tarasov Egor

import os
import requests

from typing import Any
from vacore import VACore

from g4f.client import Client
from g4f.Provider import RetryProvider, Phind, DeepInfra, Liaobots, Aichatos, You, AItianhuSpace

zammad_user_info = {}

ZAMMAD_URL = 'https://help.it4tech.ru'
ZAMMAD_API_KEY = ''

ZAMMAD_USER_INN = ''
ZAMMAD_USER_NAME = ''
ZAMMAD_USER_EMAIL = ''
ZAMMAD_USER_ISSUE = ''
ZAMMAD_USER_PHONE_NUMBER = ''

#функция на старте
def start(core: VACore):
    manifest = {
        "name": "Система автоматизации телефонной линии поддержки",
        "version": "1.0",
        "require_online": True,
        "description": "Система позволяет искать решения для клиентских проблем с помощью ChatGPT.\n"
                       "Если ответ от ChatGPT - неудовлетворительный, система формирует заявку в Zammad Helpdesk.\n",           
        "commands": {
            "поддержка" : run_start,
        }
    }
    return manifest

modname = os.path.basename(__file__)[:-3]


def start_with_options(core:VACore, manifest:dict):
    pass


def run_start(core: VACore, phrase: str):
    core.play_voice_assistant_speech("Для начала назовите ваш ИНН:")
    core.context_set(handle_current_dialogue)


def handle_current_dialogue(core: VACore, inn: str):
    if user_is_authorized(inn):
        core.play_voice_assistant_speech("Хорошо, опишите вашу проблему.")
        core.context_set(ask_chatGPT, 20)


def ask_chatGPT(core: VACore, phrase: str) -> str:
    client = Client(
        provider=RetryProvider([Phind, You, AItianhuSpace], shuffle=False)
    )
    response = client.chat.completions.create(
        model="",
        messages=[{"role": "user", "content": phrase}],
    )
    core.play_voice_assistant_speech(response.choices[0].message.content)
    core.play_voice_assistant_speech("Удалось решить проблему? да/нет")
    core.context_set(check_answer_quality, 20)


def check_answer_quality(core: VACore, phrase: str):
    if (phrase.lower() != "да"):
        core.play_voice_assistant_speech("Хорошо, повторите ваш вопрос")
        core.context_set(ask_issue, 20)
    else:
        core.play_voice_assistant_speech("Была рада помочь!")


def user_is_authorized(phrase: str):
    # Временная заглушка, интеграция с бд пока что не настроена
    inn = 1
    if inn == 1:
        return True
    return False


# Формирование заявки в Zammad Helpdesk
def submit_to_zammad(client_inn: str, zammad_user_info: dict, question: str) -> None:
    headers = {
        'Authorization': f'Bearer {ZAMMAD_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'title': f'Question from {client_inn}',
        'group': 'Техническая поддержка',
        'article': {
            'subject': 'Support request',
            'body': question,
            'type': 'note',
            'internal': False
        },
        'customer': {
            'firstname': zammad_user_info['name'],
            'email': zammad_user_info['email'],
            'phone': zammad_user_info['phone']
        },
        'note': 'forwarded by bot'
    }
    response = requests.post(ZAMMAD_URL + '/api/v1/tickets', headers=headers, json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to submit to Zammad: {response.text}")


# Функции записи информации о пользователе для формирования тикета в Zammad Helpdesk.


def ask_issue(core: VACore, phrase: str):
    if phrase:
        global ZAMMAD_USER_ISSUE
        ZAMMAD_USER_ISSUE = phrase
        core.play_voice_assistant_speech("Вопрос сохранен.")
        core.play_voice_assistant_speech("Назовите ваш ИНН.")
        core.context_set(ask_inn, 20)
    else:
        core.play_voice_assistant_speech("Не поняла, повторите, пожалуйста.")
        core.context_set(ask_issue, 20)


def ask_inn(core: VACore, phrase: str):
    if phrase:
        global ZAMMAD_USER_INN
        ZAMMAD_USER_INN = phrase
        core.play_voice_assistant_speech("ИНН сохранен.")
        core.play_voice_assistant_speech("Назовите ваши ФИО.")
        core.context_set(ask_user_name, 20)
    else:
        core.play_voice_assistant_speech("Не поняла, повторите, пожалуйста.")
        core.context_set(ask_inn, 20)


def ask_user_name(core: VACore, phrase: str):
    if phrase:
        global ZAMMAD_USER_NAME
        ZAMMAD_USER_NAME = phrase
        core.play_voice_assistant_speech("ФИО сохранены.")
        core.play_voice_assistant_speech("Назовите вашу электронную почту.")
        core.context_set(ask_user_email, 20)
    else:
        core.play_voice_assistant_speech("Не поняла, повторите, пожалуйста.")
        core.context_set(ask_user_name, 20)


def ask_user_email(core: VACore, phrase: str):
    if phrase:
        global ZAMMAD_USER_EMAIL
        ZAMMAD_USER_EMAIL = phrase
        core.play_voice_assistant_speech("Адрес эл. почты сохранен.")
        core.play_voice_assistant_speech("Назовите ваш номер телефона.")
        core.context_set(ask_user_phone_number, 20)
    else:
        core.play_voice_assistant_speech("Не поняла, повторите, пожалуйста.")
        core.context_set(ask_user_email, 20)


def ask_user_phone_number(core: VACore, phrase: str):
    if phrase:
        global ZAMMAD_USER_PHONE_NUMBER
        ZAMMAD_USER_PHONE_NUMBER = phrase
        core.play_voice_assistant_speech("Номер телефона сохранен.")
        core.play_voice_assistant_speech("Формирую заявку в Zammad Helpdesk...")

        global zammad_user_info
        zammad_user_info['name'] = ZAMMAD_USER_NAME
        zammad_user_info['email'] = ZAMMAD_USER_EMAIL
        zammad_user_info['phone'] = ZAMMAD_USER_PHONE_NUMBER

        submit_to_zammad(ZAMMAD_USER_INN, zammad_user_info, ZAMMAD_USER_ISSUE)

        core.play_voice_assistant_speech("Заявка успешно сформирована.")
        core.context_clear()