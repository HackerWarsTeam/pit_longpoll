from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll

from requests.exceptions import ReadTimeout, ConnectTimeout

import traceback
import logging
import os
import time

from vk_bot.vk_methods import VkMethods
from vk_bot.vk_events import VkEvent
from config import group_data


class VkBot:
    __slots__ = ['_events', '_name', '_token', '_group_id', '_vk', '_long_poll', 'api', 'before_start']

    def __init__(self, name: str, token: str, group_id: int) -> None:
        self._events = VkEvent()
        self._name = name
        self._token = token
        self._group_id = group_id

        self._vk = VkApi(token=self._token)
        self._long_poll = VkBotLongPoll(self._vk, self._group_id, 2)
        self.api = VkMethods(self._vk.get_api())
        self.before_start = self.startup

        return

    def startup(self):
        return

    def set_handler(self, event_type: str, handler: callable):
        if event_type in self._events.TYPES:
            setattr(self._events, event_type, handler)
        else:
            raise AttributeError(f"{event_type} is not EVENT_TYPE")
        return

    def start(self):
        logging.basicConfig(filename='logs\\BOT_ERROR.log', level=logging.ERROR)
        self.before_start()
        print(f"Bot {self._name} successfully started! Branch {os.environ.get('BRANCH', 'dev')}\n")
        try:
            while True:
                for event in self._long_poll.check():
                    # Call def ith same name as event type
                    getattr(self._events, event.type.name)(self, event)
        except (KeyboardInterrupt):
            print('Stopping . . .')
            return
        except (ReadTimeout, ConnectTimeout) as exc:
            logging.error(f"{time.strftime('%d %m %Y %H:%M:%S')}\t{traceback.format_exc(-3)}")
            print(f'\n\nTimeout error {exc}')
            print('\n\tRestarting . . .\n')
            self.start()
        except:
            logging.error(f"{time.strftime('%d %m %Y %H:%M:%S')}\t{traceback.format_exc(-3)}")
            print('Error:', end='')
            print('\n\nFull Trace')
            print(traceback.format_exc())
            print('\n\n\n\tRestarting . . .')
            self.start()
        return

    def __repr__(self) -> str:
        # Call var
        return f'<VkBot {self._name} (@id-{self._group_id})>'

    def __str__(self) -> str:
        # Call str(var)
        return f'VkBot {self._name}(@id-{self._group_id})'


if __name__ == '__main__':
    bot = VkBot('kitty_main', group_data['group_token'], group_data['group_id'])
    bot.start()
    pass
