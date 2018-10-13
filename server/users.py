from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from skyward_api import SkywardAPI
from validate_email import validate_email
from typing import Any, Dict
from os import environ
from pickle import dumps
import bcrypt
import random, string

client = MongoClient("mongodb://{0}:{1}@ds223653.mlab.com:23653/updater".format(
        environ["db_user"],
        environ["db_pass"]
))
db = client["updater"]
users_collection = db["users"]

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
    if users_collection.find_one({
        "email": email
    }) is not None:
        raise ValueError("Email already used.")
    u_id = make_id(20)
    while users_collection.find_one({
        "_id": u_id
    }) is not None:
        u_id = make_id(20)
    hashed_pw = bcrypt.hashpw(password1.encode(), bcrypt.gensalt())
    user_obj = {
        "email": email,
        "password": hashed_pw,
        "sky_data": {},
        "service": "",
        "grades": {},
        "_id": u_id
    }
    users_collection.insert_one(user_obj)



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
    user = users_collection.find_one({
        "email": email
    })
    if user is None:
        raise ValueError("Incorrect email/password.")

    user_password = user["password"]
    if not bcrypt.checkpw(password.encode(), user_password):
        raise ValueError("Incorrect email/password.")

    return user

def get_user_by_id(u_id: str) -> ReturnDocument:
    return users_collection.find_one({
        "_id": u_id
    })

def update_user(u_id: str, data: Dict[str, Any]) -> None:
    user = users_collection.update_one({
        "_id": u_id
    }, {
        "$set": data
    })
