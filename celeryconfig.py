from os import environ

broker_url = environ["REDIS_URL"]
result_backend = environ["REDIS_URL"]

task_serializer = 'pickle'
result_serializer = 'pickle'

accept_content = ['pickle']
task_always_eager = False
