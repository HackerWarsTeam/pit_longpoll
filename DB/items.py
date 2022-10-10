from DB.instance import DB
import mysql.connector.errors as sql_err
import json
import os


def check_items():
    QUERY = 'INSERT INTO `items` VALUES (%s, %s);'
    items = json.loads(open(os.environ.get('ITEM_FILE'), 'r').read())

    for i in items:
        data = (i, items[i])
        DB().query(QUERY, data)
    return


def get_item_by_id(item_id: int):
    QUERY = 'SELECT item_name FROM items WHERE item_id = %s;'

    try:
        item_id = int(item_id)
    except ValueError:
        raise TypeError(f"`item_id` must be int, got {item_id} instead")

    res = DB().query(QUERY, (item_id,))
    if res:
        res = res[0]
        return res[0]
    else:
        return


def get_item_by_name(name: str):
    QUERY = "SELECT item_id FROM items WHERE item_name LIKE CONCAT('%', %s, '%');"

    res = DB().query(QUERY, (name,))

    if res:
        res = res[0]
        return res[0]
    else:
        return


def search_item(name: str):
    QUERY = "SELECT COUNT(*) FROM items WHERE item_name LIKE CONCAT('Книга - ', %s, '%');"

    cnt = DB().query(QUERY, (name,))[0][0]
    if cnt > 0:
        QUERY = "SELECT * FROM items WHERE item_name LIKE CONCAT('Книга - ', %s, '%');"
    else:
        QUERY = "SELECT * FROM items WHERE item_name LIKE CONCAT(%s, '%');"

    # QUERY = "SELECT * FROM items WHERE item_name LIKE CONCAT('%', %s, '%');"

    res = DB().query(QUERY, (name,))
    if res:
        data = {'count': 0, 'result': []}
        for row in res:
            data['result'].append({'item_id': row[0], 'item_name': row[1]})
        data['count'] = len(data['result'])
        return data
    else:
        return


if __name__ == '__main__':
    print(get_item_by_name('Книга - Браконьер'))
    print(get_item_by_id(14972))
    print(search_item('рас'))
    # check_items()
