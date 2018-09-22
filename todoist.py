import requests
import json
import pika
import time

API_TOKEN = '-'
QUEUE = 'trello-cards'

class TodoistClient(object):

    def __init__(self, api_token):
        self._api_token = api_token
        self._project_cache = {}

    def create_project(self, name, id):
        if id in self._project_cache:
            return self._project_cache[id]

        data = {'name': name}
        resp = self._post('/projects', data, id)
        if resp is not None:
            self._project_cache[id] =  resp['id']
            return self._project_cache[id]

        return None
        
    def create_task(self, task, id):
        resp = self._post('/tasks', task)
        return resp['id']

    def create_comment(self, comment):
        self._post('/comments', comment)

    def _post(self, path, data, request_id=None):
        headers = {'Authorization': f'Bearer {self._api_token}'}

        if request_id is not None:
            headers['X-Request-Id'] = request_id

        r = requests.post('https://beta.todoist.com/API/v8' + path, 
                          headers=headers,
                          json=data)

        if r.status_code == 200:
            return r.json()

        print(r.text)
        return None

def handle_card(todoist):
    def handle(ch, method, properties, body):
        time.sleep(5)
        print('Received', body)
        message = json.loads(body)

        try:
            create_on_todoist(todoist, message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except:
            print('An error has ocurred')

    return handle


def create_on_todoist(todoist, message):
    project_id = todoist.create_project(message['project'], 
                                        message['project_id'])
        
    task_id = todoist.create_task({
        'content': message['name'],
        'project_id': project_id,
        'due_datetime': message['due']
    }, message['id'])

    for content in message['notes']:
        todoist.create_comment({
            'content': content,
            'task_id': task_id
        })

if __name__ == '__main__':
    todoist = TodoistClient(API_TOKEN)
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE, durable=True)

    channel.basic_consume(handle_card(todoist), queue=QUEUE)

    print("[*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()