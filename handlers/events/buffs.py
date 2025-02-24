import time

import vk_api
from vk_api.longpoll import VkEventType, VkLongPoll, CHAT_START_ID

from ORM import Session, BuffUser, BuffCmd, UserInfo

from dictionaries.buffs import POSSIBLE_ANSWERS, BUFF_RACE, SUCCESS_ANSWER
from dictionaries.emoji import gold

from config import OVERSEER_BOT, APO_PAYMENT


def buff(vk_id: int, chat_id: int, msg_id: int, command: int, receiver: int):
    DB = Session()
    buffer: BuffUser = DB.query(BuffUser).filter(BuffUser.buff_user_id == vk_id).first()
    cmd: BuffCmd = DB.query(BuffCmd).filter(BuffCmd.buff_cmd_id == command).first()
    msg = cmd.buff_cmd_text
    if 'race1' in msg:
        msg = msg.replace('race1', BUFF_RACE[buffer.buff_user_race1])
    if 'race2' in msg:
        msg = msg.replace('race2', BUFF_RACE[buffer.buff_user_race2])
    peer = CHAT_START_ID + buffer.buff_user_chat_id

    vk = vk_api.VkApi(token=buffer.buff_user_token, api_version='5.131')
    api = vk.get_api()
    long_poll = VkLongPoll(vk, 1)

    msg_id = api.messages.getByConversationMessageId(
        peer_id=peer,
        conversation_message_ids=msg_id
    )['items'][0]['id']

    api.messages.send(
        peer_ids=[OVERSEER_BOT],
        message=msg,
        random_id=0,
        forward_messages=str(msg_id)
    )

    res = read(long_poll)
    if not res:
        return
    if SUCCESS_ANSWER not in res:
        return res
    res = res.split('\n')[0]

    # Change balance
    user_from: UserInfo = DB.query(UserInfo).filter(UserInfo.user_id == receiver).first()
    user_to: UserInfo = DB.query(UserInfo).filter(UserInfo.user_id == buffer.buff_user_id).first()

    if user_from.user_role.role_can_balance:
        user_from.balance -= APO_PAYMENT

    user_to.balance += APO_PAYMENT
    DB.add(user_from)
    DB.add(user_to)

    DB.commit()

    res += f"\n[id{user_from.user_id}|На счету]: {user_from.balance}{gold}"
    DB.close()
    return res


def read(lp: VkLongPoll) -> str:
    for i in range(6):
        time.sleep(0.5)
        try:
            events = lp.check()
        except TypeError:
            events = lp.check()
            pass
        for event in events:
            if event.type != VkEventType.MESSAGE_NEW:
                continue

            if not event.from_group:
                continue

            if event.from_me:
                continue

            if not event.peer_id == OVERSEER_BOT:
                continue

            if not any([msg in event.message for msg in POSSIBLE_ANSWERS + (SUCCESS_ANSWER,)]):
                continue
            return event.message
