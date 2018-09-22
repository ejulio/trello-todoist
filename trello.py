import requests
import pika
import json


API_KEY = '-'
API_TOKEN = '-'
QUEUE = 'trello-cards'


class TrelloClient(object):

    def __init__(self, api_key, api_token):
        self._api_key = api_key
        self._api_token = api_token

    def active_cards_from_list(self, list_id):
        params = {
            'fields': 'id,name,due,desc,visible',
            'attachments': 'true',
            'attachment_fields': 'url,isUpload'
        }
        cards = self._get(f'/lists/{list_id}/cards', params)
        return cards

    def active_lists(self):
        for board in self._active_boards():
            lists = self._get(f'/boards/{board["id"]}/lists/')
        
            for list in lists:
                if not list['closed']:
                    yield list 

    def _active_boards(self):
        boards = self._get('/members/me/boards')
        return filter(lambda b: not b['closed'], boards)

    def _get(self, path, params=None):
        params = {} if params is None else params
        params['key'] = self._api_key
        params['token'] = self._api_token
        r = requests.get('https://api.trello.com/1' + path, params=params)
        return r.json()


def should_migrate(prompt):
    answer = input(prompt)
    answer = 'y' if answer == '' else answer
    return answer.lower() == 'y'


def trello_lists_to_migrate(trello):
    for list in trello.active_lists():
        if should_migrate(f'Do you want to migrate {list["name"]}? [y]/n '):
            yield (list['id'], list['name'])


def trello_card_to_todoist_comments(card):
    if card['desc'] is not None and card['desc'] != '':
        yield card['desc'].replace('\n', '')

    if card['attachments'] is not None:
        for attachment in card['attachments']:
            if not attachment['isUpload']:
                yield attachment['url']


if __name__ == '__main__':
    trello = TrelloClient(API_KEY, API_TOKEN)
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE, durable=True)

    lists = list(trello_lists_to_migrate(trello))

    for (id, name) in lists:
        print(f'Migrating cards from {name}')
        
        cards = trello.active_cards_from_list(id)
        for card in cards:
            print('Migrating', card)
            message = {
                'id': card['id'],
                'name': card['name'],
                'due': card['due'],
                'project': name,
                'project_id': id,
                'notes': list(trello_card_to_todoist_comments(card))
            }
            message = json.dumps(message)
            channel.basic_publish(exchange='',
                        routing_key=QUEUE,
                        body=message,
                        properties=pika.BasicProperties(
                            delivery_mode=2
                        ))

    connection.close()