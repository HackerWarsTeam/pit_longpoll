from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll

from time import strftime
from requests.exceptions import ReadTimeout

import traceback
import os
from signal import signal, SIGTERM

from vk_bot.vk_methods import VkMethods
from vk_bot.vk_events import VkEvent

from logger import get_logger


class VkBot:
    # __slots__ = ['_events', '_name', '_token', '_group_id', '_vk', '_long_poll', 'api', '_before_start', '_before_stop']
    __not_kill = True

    def __init__(self, token: str) -> None:
        self._events = VkEvent()
        self._token = token

        self._vk = VkApi(token=self._token, api_version='5.131')
        self.api = VkMethods(self._vk.get_api())
        self._name = self.api.get_group_name()
        self._group_id = self.api.group_id()

        self._long_poll = VkBotLongPoll(self._vk, self._group_id, 2)

        self._before_start = None
        self._before_stop = None

        return

    def set_start(self, func: callable):
        self._before_start = func
        return

    def startup(self):
        def wrapper(func: callable):
            self.set_start(func)
            return
        return wrapper

    def set_stop(self, func: callable):
        self._before_stop = func
        signal(SIGTERM, self._before_stop)
        return

    def on_stop(self):
        def wrapper(func: callable):
            self.set_stop(func)
            return
        return wrapper

    def set_handler(self, event_type: str, handler: callable):
        if event_type in self._events.TYPES:
            setattr(self._events, event_type, handler)
        else:
            raise AttributeError(f"{event_type} is not EVENT_TYPE")
        return

    def event_handler(self, event_type: str):
        # decorator for set_handler
        def wrapper(handler: callable, *args, **kwargs):
            self.set_handler(event_type, handler)

        return wrapper

    def start(self):
        # logger = get_logger(__name__, '_BOT_EVENTS', 'midnight')
        # logger_errors = get_logger(__name__, '_BOT_ERRORS', 'midnight')
        if self._before_start:
            print('Starting up . . .')
            self._before_start(self)
            print('Started up')

        print(f"[{strftime('%d.%m.%y %H:%M:%S')}] "
              f"Bot {self._name} successfully started! Branch {os.environ.get('BRANCH', 'dev')}\n")
        while self.__not_kill:
            try:
                for event in self._long_poll.check():
                    # Call def with same name as event type
                    # logger.info(f"{event.type.name}:\t{event.raw['event_id']} - {str(event.obj).encode('cp1251', 'xmlcharrefreplace').decode('cp1251')}")
                    getattr(self._events, event.type.name)(self, event)
            except KeyboardInterrupt:
                print('\n', 'Stopping . . .', '\n')
                self.__not_kill = False
                if self._before_stop:
                    self._before_stop(self)
                return
            except ReadTimeout as exc:
                # logger_errors.warning("ReadTimeout")
                # print(f'\n\nTimeout error {exc}')
                # print('\n\tRestarting . . .\n')
                print(f"\n[{strftime('%d.%m.%y %H:%M:%S')}] Timeout error\nRestarting . . .")
                pass
            except:
                # logger_errors.error("Un-handled exception ! ! !", exc_info=True)
                # logging.error(f"{time.strftime('%d %m %Y %H:%M:%S')}\t{traceback.format_exc(-3)}")
                print('Error:', end='')
                print('\n\nFull Trace')
                print(traceback.format_exc())
                print(f"\n\n\n\t[{strftime('%d.%m.%y %H:%M:%S')}] Restarting . . .")
        return

    def __repr__(self) -> str:
        # Call var
        return f'<VkBot {self._name} (@id-{self._group_id})>'

    def __str__(self) -> str:
        # Call str(var)
        return f'VkBot {self._name}(@id-{self._group_id})'
