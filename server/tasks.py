from celery import Celery
from typing import Dict, List
from skyward_api import SkywardAPI, SkywardClass
from os import environ

app = Celery("server.tasks")
app.config_from_object("celeryconfig")

@app.task
def login_task(
    username: str,
    password: str,
    service: str,
) -> Dict[str, str]:
    try:
        api = SkywardAPI(service)
        api.setup(username, password)
        sess_data = api.get_session_params()
        return sess_data
    except ValueError:
        return {
            "error": "U/P"
        }

@app.task
def get_grades_task(
    service: str,
    sky_data: Dict[str, str],
) -> List[SkywardClass]:
    api = SkywardAPI.from_session_data(service, sky_data, timeout=60)
    grades = api.get_grades()
    return grades
