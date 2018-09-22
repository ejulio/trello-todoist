import requests
import time


API_KEY = '-'
API_TOKEN = '-'
TODOIST_API_TOKEN = '-'


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


class TodoistClient(object):

	def __init__(self, api_token):
		self._api_token = api_token

	def create_project(self, name, id):
		data = {'name': name}
		resp = self._post('/projects', data, id)
		return resp['id']

	def create_task(self, task):
		resp = self._post('/tasks', task)
		return resp['id']

	def create_comments(self, comments):
		for comment in comments:
			resp = self._post('/comments', comment)

	def _post(self, path, data, id=None):
		headers = {
			'Authorization': f'Bearer {self._api_token}'
		}
		r = requests.post('https://beta.todoist.com/API/v8' + path, 
						  headers=headers,
						  json=data)
		if r.status_code == 200:
			return r.json()
		
		print(r.status_code, r.text)


def should_migrate(prompt):
	answer = input(prompt)
	answer = 'y' if answer == '' else answer
	return answer.lower() == 'y'


def trello_card_to_todoist_task(card, project_id):
	return {
		'content': card['name'],
		'project_id': project_id,
		'due_datetime': card['due']
	}


def trello_card_to_todoist_comments(card, task_id):
	if card['desc'] is not None and card['desc'] != '':
		yield {
			'task_id': task_id,
			'content': card['desc']
		}

	if card['attachments'] is not None:
		for attachment in card['attachments']:
			if not attachment['isUpload']:
				yield {
					'task_id': task_id,
					'content': attachment['url']
				}


def trello_lists_to_migrate(trello):
	for list in trello.active_lists():
		if list['name'] == 'Software development':
		#if should_migrate(f'Do you want to migrate {list["name"]}? [y]/n '):
			yield (list['id'], list['name'])


if __name__ == '__main__':
	trello = TrelloClient(API_KEY, API_TOKEN)
	todoist = TodoistClient(TODOIST_API_TOKEN)

	lists = list(trello_lists_to_migrate(trello))

	for (id, name) in lists:
		print(f'Migrating {name}')
		project_id = todoist.create_project(name, id)
		
		cards = trello.active_cards_from_list(id)
		for card in cards:
			time.sleep(1)
			print('Migrating', card)
			task = trello_card_to_todoist_task(card, project_id)
			task_id = todoist.create_task(task)

			comments = trello_card_to_todoist_comments(card, task_id)
			todoist.create_comments(comments)
		