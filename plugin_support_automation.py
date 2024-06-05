# Tech-support line automation plugin
# Ключ для общения с СhatGPT можно получить на https://vsegpt.ru
# author: Tarasov Egor

from vacore import VACore
from plugin_boltalka_vsegpt import run_start

#функция на старте
def start(core: VACore):
    manifest = {
        "name": "Система автоматизации телефонной линии поддержки",
        "version": "1.0",
        "require_online": True,
        "description": "Система позволяет искать решения для клиентских проблем с помощью ChatGPT.\n"
                       "Если ответ от ChatGPT - неудовлетворительный, система формирует заявку в Zammad Helpdesk.\n",
        "commands": {
            "задать вопрос|начать" : run_start,
        }
    }
    return manifest


def run_start():
    pass


def ask_chat_GPT():
    pass


def user_is_authorized():
    pass


def form_zammad_request():
    pass