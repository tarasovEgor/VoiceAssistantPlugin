# Tech-support line automation plugin
# Ключ для общения с СhatGPT можно получить на https://vsegpt.ru
# author: Tarasov Egor

import os
import openai
import asterisk.manager

from typing import Any
from vacore import VACore
from asterisk.manager import Manager
from plugin_boltalka_vsegpt import new_chat, boltalka

#функция на старте
def start(core: VACore):
    manifest = {
        "name": "Система автоматизации телефонной линии поддержки",
        "version": "1.0",
        "require_online": True,
        "description": "Система позволяет искать решения для клиентских проблем с помощью ChatGPT.\n"
                       "Если ответ от ChatGPT - неудовлетворительный, система формирует заявку в Zammad Helpdesk.\n",
        "options_label": {
            "apiKey": "API-ключ VseGPT для доступа к ChatGPT",
            "apiBaseUrl": "URL для OpenAI (нужен, если вы связываетесь с другим сервером, эмулирующим OpenAI)",
            "system": "Вводная строка, задающая характер ответов помощника.",
            "model": "ID нейросетевой модели с сайта Vsegpt",
            "model_spravka": "ID нейросетевой модели с сайта Vsegpt для справок (точных фактов)",
        },               
        "commands": {
            "задать вопрос|начать" : run_start,
        }
    }
    return manifest

modname = os.path.basename(__file__)[:-3]

def run_start(core: VACore):
    manager = connect_to_asterisk()

    #Ожидание входящего звонка
    while True:
        event = manager.wait_for_event('Newchannel')
        if event and event.get('Channel'):
            channel = event.get('Channel')
            print(f"New call on channel: {channel}")

            core.context_set(handle_incoming_call)
            
            break

    manager.close()


# Подключение к серверу Asterisk
def connect_to_asterisk():
    manager = asterisk.manager.Manager()
    manager.connect('asterisk-server-ip-address')
    manager.login('username', 'password')
    return manager


# Перенаправление звонка в случае несовпадения ИНН
def redirect_call(manager, channel, context, extension, priority):
    try:
        manager.redirect(channel=channel, context=context, exten=extension, priority=priority)
        print(f"Call redirected to {context}, extension {extension}, priority {priority}")
    except asterisk.manager.ManagerSocketException as e:
        print(f"Error connecting to the manager: {e}")
    except asterisk.manager.ManagerAuthException as e:
        print(f"Error logging in to the manager: {e}")
    except asterisk.manager.ManagerException as e:
        print(f"Error: {e}")


# Обработка входящего звонка
def handle_incoming_call(core: VACore, phrase: str, manager: Manager, channel: Any):
    core.play_voice_assistant_speech("Добрый день! Для начала назовите ваш ИНН")
    if user_is_authorized(phrase):
        if phrase: 
            core.context_set(ask_chat_GPT)
        core.play_voice_assistant_speech("Спасибо за обращение в нашу службу поддержки!")
    else:
        core.play_voice_assistant_speech("К сожалению ИНН не был найден в нашей базе, перенаправляю ваш звонок на специалиста.")
        redirect_call(manager, channel, 'incoming', '+7XXXXXXXXXX', 1)


def ask_chat_GPT(core: VACore, phrase: str):
    options = core.plugin_options(modname)

    openai.api_key = options["apiKey"]
    openai.api_base = options["apiBaseUrl"]

    new_chat(core)

    core.play_voice_assistant_speech("Хорошо, опишите вашу проблему.")

    if phrase:
        core.play_voice_assistant_speech("Обрабатываю запрос")
        core.context_set(boltalka, 20)
        core.play_voice_assistant_speech("Помог ли вам данный ответ? Да или нет")
        if phrase == "да":
            core.play_voice_assistant_speech("Отлично, всегда рада помочь!")
        elif phrase == "нет":
            core.play_voice_assistant_speech("Извините, попробуйте задать вопрос повторно")
            core.context_set(boltalka, 20)
        else:
            core.play_voice_assistant_speech("Хорошо, формирую заявку в Zammad Helpdesk")
            core.context_set(form_zammad_request)
            return
    else:
        boltalka(core, phrase)


def user_is_authorized(phrase: str):
    # Временная заглушка, интеграция с бд пока что не настроена
    inn = None # конвертация фразы в числовой формат
    db = None
    if inn in db:
        return True
    return False

# Формирование заявки в Zammad Helpdesk
def form_zammad_request(core: VACore, phrase: str):
    core.play_voice_assistant_speech("Назовите ваше имя")
    user_name = phrase

    core.play_voice_assistant_speech("Назовите ваш ИНН")
    user_inn = phrase

    core.play_voice_assistant_speech("Назовите ваш номер телефона")
    phone_number = phrase

    core.play_voice_assistant_speech("Опишите проблему")
    issue_description = phrase

    core.play_voice_assistant_speech("В какое время вам будет удобно связаться с нашим специалистом?")
    convenient_time = phrase

    issue_report = "User INN: {}\nUser Name: {}\nPhone Number: {}\nIssue Description: {}\nConvenient Time: {}".format(
        user_inn,
        user_name,
        phone_number,
        issue_description,
        convenient_time
    )

    post_zammad_request(issue_report)

    core.play_voice_assistant_speech("Заявка успешно оформлена, ожидайте, скоро с вами свяжется наш специалист")
    return


# Отправка заявки в Zammad Helpdesk (пока что не реализована)
def post_zammad_request(issue_report: str):
    pass