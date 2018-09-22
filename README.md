# trello-todoist
This is a simple project to migrate Trello cards to Todoist tasks:
* Trello lists become Todoist projects.
* Card names become task names
* Card description and url attachments become task notes

I used requests and pika (RabbitMQ library for Python) to handle this transition.

First of all:
* Get a Trello API KEY and API TOKEN and set them on `trello.py`
* Get a Todoist API KEY and set in `todoist.py`
* Start a RabbitMQ (if you use docker it could be something like `docker run -p 5672:5672 rabbitmq`)

Now, if you run `trello.py` if will prompt what lists do you want to migrate.
Each card will be sent as a message to RabbitMQ.
When you run `todoist.py` it will handle all messages sent from `trello.py`.

Some issues:
* If there is a problem creating the project, it will create cards in *Inbox*.
* If any message fails, it will be `unacked` in RabbitMQ and `todoist.py` should be restarted to reprocess this message
* In the previous scenarion, the message will, probably, be sent to *Inbox*
* It waits 5s to process each message because Todoist was blocking the requests
