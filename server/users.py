from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from skyward_api import SkywardAPI
from validate_email import validate_email
from typing import Any, Dict
from os import environ
import bcrypt
import random, string

client = MongoClient("mongodb://{0}:{1}@ds223653.mlab.com:23653/updater".format(
        environ["db_user"],
        environ["db_pass"]
))
db = client["updater"]
collect = db["users"]

def make_id(length: int) -> str:
    return ''.join(
        random.SystemRandom().choice(
            string.ascii_uppercase + string.digits
        ) for _ in range(length)
    )

def register(
    email: str,
    password1: str,
    password2: str
) -> None:
    """Registers a user.

    Parameters
    ----------
    email : str
        Email of user.
    password1 : str
        Password for user.
    password2 : str
        Confirmation of password.

    Side-Effects
    ------------
    Inserts a user into the users collection.

    Raises
    -------
    ValueError
        If passwords do not match or if emails are invalid.

    """
    if password1 != password2:
        raise ValueError("Password1 must be the same as password2.")
    if not validate_email(email):
        raise ValueError("Email must be a valid email.")
    if collect.find_one({
        "email": email
    }) is not None:
        raise ValueError("Email already used.")
    u_id = make_id(20)
    while collect.find_one({
        "_id": u_id
    }) is not None:
        u_id = make_id(20)
    hashed_pw = bcrypt.hashpw(password1.encode(), bcrypt.gensalt())
    user_obj = {
        "email": email,
        "password": hashed_pw,
        "sky_data": {},
        "service": "",
        "notifying": False,
        "_id": u_id
    }
    collect.insert_one(user_obj)



def login(
    email: str,
    password: str
) -> ReturnDocument:
    """Logs a user in and gets their user id.

    Parameters
    ----------
    email : str
        User's email.
    password : str
        User's password.

    Returns
    -------
    str
        Session id for user.

    Raises
    -------
    ValueError
        Incorrect email password combination.

    """
    user = collect.find_one({
        "email": email
    })
    if user is None:
        raise ValueError("Incorrect email/password.")

    user_password = user["password"]
    if not bcrypt.checkpw(password.encode(), user_password):
        raise ValueError("Incorrect email/password.")

    return user

def get_user_by_id(u_id: str) -> ReturnDocument:
    return collect.find_one({
        "_id": u_id
    })

def update_user(u_id: str, data: Dict[str, Any]) -> None:
    user = collect.update_one({
        "_id": u_id
    }, {
        "$set": data
    })

def add_notify(u_id: str) -> None:
    notify_collect = db["notify"]
    prev_notif = notify_collect.find_one({
        "_id": u_id
    })
    if prev_notif is not None:
        raise ValueError("Already in notification db!")
    user = collect.find_one({
        "_id": u_id
    })
    sky_data = user["sky_data"]
    email = user["email"]
    service = user["service"]
    curr_grades = SkywardAPI.from_session_data(service, sky_data).get_grades_json()
    notify_collect.insert_one({
        "_id": u_id,
        "grades": curr_grades,
    })
