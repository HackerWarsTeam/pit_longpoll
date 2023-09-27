from datetime import datetime

from config import GUILD_NAME, GUILD_CHAT_ID

from ORM import session, UserInfo, UserStats, Logs, Item

from utils.parsers import parse_profile, parse_storage_action, get_transfer
from utils.formatters import str_datetime, datediff
from utils.math import commission_price
import dictionaries.emoji as emo
from dictionaries import items

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vk_bot.vk_bot import VkBot
    from vk_api.bot_longpoll import VkBotEvent


def bot_message(self: "VkBot", event: "VkBotEvent"):
    # group's message in chat

    if "Ваш профиль:" in event.message.text:
        Logs(event.message.from_id, 'Profile_message', event.message.text).make_record()
        msg_id = self.api.send_chat_msg(event.chat_id, 'Читаю профиль...')[0]
        answer = profile_message(self, event)
        photo = ''
        if event.chat_id == GUILD_CHAT_ID:
            if event.message['attachments']:
                if 'photo' in event.message['attachments'][0]:
                    at = event.message['attachments'][0]
                    photo = f"photo{at['photo']['owner_id']}_{at['photo']['id']}_{at['photo']['access_key']}"
            msg_id_del = self.api.get_conversation_msg(event.message.peer_id, event.message.conversation_message_id)['id']
            # self.api.del_msg(event.message.peer_id, msg_id_del)
        self.api.edit_msg(msg_id['peer_id'], msg_id['conversation_message_id'], answer,
                          attachment=photo if photo else None)

    if 'положили' in event.message.text or 'взяли' in event.message.text:
        if event.chat_id == GUILD_CHAT_ID:
            storage_reactions(self, event)
            pass

    if 'от игрока' in event.message.text:
        if event.chat_id == GUILD_CHAT_ID:
            Logs(event.message.from_id, 'Guild_Transfer', event.message.text).make_record()
            transfer_logging(self, event)
            pass
    return


def profile_message(self: "VkBot", event: "VkBotEvent") -> str:
    DB = session()
    data = parse_profile(event.message.text)
    info: UserInfo = DB.query(UserInfo).filter(UserInfo.user_id == data['id_vk']).first()

    new_data = (data['level'], data['attack'], data['defence'],
                data['strength'], data['agility'], data['endurance'],
                data['luck'])
    if info:
        stats: UserStats = info.user_stats

        answer = f"{data['name']}, статы обновлены! ({datediff(stats.last_update, datetime.now())} с {str_datetime(stats.last_update)})\n" \
                 f"[ {data['class_name']} | {data['race']} ]\n" \
                 f"{emo.level}{data['level']}({data['level'] - stats.user_level}) " \
                 f"{emo.attack}{data['attack']}({data['attack'] - stats.user_attack}) " \
                 f"{emo.defence}{data['defence']}({data['defence'] - stats.user_defence})\n" \
                 f"{emo.strength}{data['strength']}({data['strength'] - stats.user_strength}) " \
                 f"{emo.agility}{data['agility']}({data['agility'] - stats.user_agility}) " \
                 f"{emo.endurance}{data['endurance']}({data['endurance'] - stats.user_endurance})\n" \
                 f"{emo.luck}{data['luck']}({data['luck'] - stats.user_luck})\n" \
                 f"(До пинка {(data['level'] + 15) * 6 - data['strength'] - data['agility']}{emo.strength}/{emo.agility}" \
                 f" или {(data['level'] + 15) * 3 - data['endurance']}{emo.endurance})"
    else:
        info = UserInfo(user_id=data['id_vk'])

        stats = UserStats(user_id=data['id_vk'])

        answer = f"{data['name']}, статы записаны!\n" \
                 f"[ {data['class_name']} | {data['race']} ]\n" \
                 f"{emo.level}{data['level']} {emo.attack}{data['attack']} {emo.defence}{data['defence']} " \
                 f"{emo.strength}{data['strength']} {emo.agility}{data['agility']} {emo.endurance}{data['endurance']} " \
                 f"{emo.luck}{data['luck']}\n" \
                 f"(До пинка {(data['level'] + 15) * 6 - data['strength'] - data['agility']}{emo.strength}/{emo.agility}" \
                 f"{(data['level'] + 15) * 3 - data['endurance']}{emo.endurance})"

    stats.user_level, stats.user_attack, stats.user_defence, \
        stats.user_strength, stats.user_agility, stats.user_endurance, \
        stats.user_luck = new_data

    in_guild_roles = [0, 1, 2, 3, 4, 5, 6, 7, 11]

    if data['guild'] == GUILD_NAME:
        if info.role_id is None \
                or info.role_id not in in_guild_roles:
            answer = 'Обновил информацию гильдии!\n' + answer
            info.role_id = role_guild = 5
    else:
        if info.role_id is None \
                or info.role_id not in in_guild_roles:
            # if not banned and not in guild now
            if info.role_id != 9:
                info.role_id = other_role = 8

    DB.add(info)
    DB.add(stats)
    DB.commit()
    DB.close()
    return answer


def storage_reactions(self: "VkBot", event: "VkBotEvent"):
    data = parse_storage_action(event.message.text)
    if data['item_type'] == 'item':
        return
    DB = session()
    user: UserInfo = DB.query(UserInfo).filter(UserInfo.user_id == data['id_vk']).first()
    if data['item_type'] == 'book':
        user.balance += data['result_price'] * data['count']
        DB.add(user)
        DB.commit()

        Logs(user.user_id, 'Storage',
             f"-{data['count']}*{data['item_name']}; +{data['result_price']}"
             if data['result_price'] > 0
             else f"+{data['count']}*{data['item_name']}; {data['result_price']}",
             on_user_id=user.user_id).make_record()

        msg = f"[id{user.user_id}|Готово], "
        msg += "пополняю баланс на" if data['result_price'] > 0 else "списываю с баланса"
        msg += f" {abs(data['result_price'] * data['count'])}{emo.gold}"
        msg += f"({data['count']}*{abs(data['result_price'])})\n" if data['count'] > 1 else "\n"

        msg += f"Ваш долг: {emo.gold}{-int(user.balance)}(Положить {commission_price(-int(user.balance))})" \
            if user.balance < 0 else f"Сейчас на счету: {emo.gold}{user.balance}"
        self.api.send_chat_msg(event.chat_id, msg)
        return

    if data['item_type'] == 'gold':
        user.balance += data['count']
        DB.add(user)
        DB.commit()
        Logs(user.user_id, 'Storage',
             data['count'],
             on_user_id=user.user_id).make_record()
        if data['count'] < 0:
            msg = f"О, [id{data['id_vk']}|Вы] взяли {-data['count']} золота!\n"
        else:
            msg = f"О, [id{data['id_vk']}|Вы] положили {data['count']} золота!\n"
        msg += f"Ваш долг: {emo.gold}{-int(user.balance)}(Положить {commission_price(-int(user.balance))})" \
            if user.balance < 0 else f"Сейчас на счету: {emo.gold}{user.balance}"
        self.api.send_chat_msg(event.chat_id, msg)
        return
    DB.close()
    return


def transfer_logging(self: "VkBot", event: "VkBotEvent"):
    _items_to_log = (items.valuables + items.adm_items + items.adm_ingredients +
                     items.ordinary_books_active + items.ordinary_books_passive)
    data = get_transfer(event.message.text)
    from_name, to_name = self.api.get_names([data['from_id'], data['to_id']], 'nom').split(',')
    with session() as s:
        item: Item = s.query(Item).filter(Item.item_name == data['item_name'], Item.item_has_price == True).first()
    if item.item_id not in _items_to_log:
        return

    msg = f'{from_name} отправил {to_name}\n{item.item_name}\n'
    self.api.send_log(msg)
    return
