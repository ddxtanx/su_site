from os import environ
from kombu_fernet.serializers.pickle import MIMETYPE
broker_url = environ["REDIS_URL"]
result_backend = environ["REDIS_URL"]

task_serializer = "fernet_pickle"
result_serializer = "fernet_pickle"

accept_content = [MIMETYPE, 'pickle', 'fernet_pickle', "pickle (application/x-python-serialize)"]
task_always_eager = False
