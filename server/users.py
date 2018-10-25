from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from pymongo.errors import AutoReconnect
from skyward_api import SkywardAPI, SkywardClass
from validate_email import validate_email
from typing import Any, Dict, List
from os import environ
from pickle import dumps, loads
import bcrypt
import random, string

client = MongoClient("mongodb://{0}:{1}@ds223653.mlab.com:23653/updater".format(
        environ["db_user"],
        environ["db_pass"]
))
db = client["updater"]
users_collection = db["users"]

def reset_connection():
    global client, db, users_collection
    client.close()
    client = MongoClient("mongodb://{0}:{1}@ds223653.mlab.com:23653/updater".format(
            environ["db_user"],
            environ["db_pass"]
    ))
    db = client["updater"]
    users_collection = db["users"]

def get_users() -> List[Any]:
    try:
        return list(users_collection.find())
    except AutoReconnect:
        reset_connection()
        return list(users_collection.find())

def get_user_by_query(query: Dict[Any, Any]) -> Any:
    try:
        return users_collection.find_one(query)
    except AutoReconnect:
        reset_connection()
        return users_collection.find_one(query)

def update_user_by_query(id_info: Dict[Any, Any], update_info: Dict[Any, Any]) -> None:
    try:
        users_collection.update(id_info, {
            "$set": update_info
        })
    except AutoReconnect:
        reset_connection()
        users_collection.update(id_info, {
            "$set": update_info
        })

class User():
    def __init__(
        self,
        u_id: str,
        email: str,
        sky_data: Dict[str, str],
        service: str,
        grades: List[SkywardClass]
    ) -> None:
        self.id = u_id
        self.email = email
        self.sky_data = sky_data
        self.service = service
        self.grades = grades

    @staticmethod
    def from_login(
        email: str,
        password: str
    ) -> "User":
        try:
           user = login(email, password)
           return User(
              user["_id"],
              user["email"],
              user["sky_data"],
              user["service"],
              loads(user["grades"])
           )
        except ValueError:
           return None

    @staticmethod
    def from_id(u_id: str) -> "User":
        if u_id == "":
            return None
        user = get_user_by_id(u_id)
        return User(
            user["_id"],
            user["email"],
            user["sky_data"],
            user["service"],
            loads(user["grades"])
         )

    def is_authenticated(self) -> bool:
        return self.email != ""

    def is_active(self) -> bool:
        #Change if user system changes
        return self.is_authenticated() and self.sky_data != {}

    def is_anonymous(self) -> bool:
        return True

    def get_id(self) -> str:
        return self.id

    def set_sky_data(
        self,
        sky_data: Dict[str, str]
    ) -> None:
        self.sky_data = sky_data
        update_user(self.id, {
            "sky_data": sky_data
        })

    def set_service(
        self,
        service: str
    ) -> None:
        self.service = service
        update_user(self.id, {
            "service": service
        })

    def set_grades(
        self,
        grades: List[SkywardClass]
    ) -> None:
        self.grades = grades
        update_user(self.id, {
            "grades": dumps(grades)
        })

def add_user(data: Dict[Any, Any]) -> None:
    try:
        users_collection.insert_one(data)
    except AutoReconnect:
        reset_connection()
        users_collection.insert_one(data)

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
    if get_user_by_query({
        "email": email
    }) is not None:
        raise ValueError("Email already used.")
    u_id = make_id(20)
    while get_user_by_id(u_id) is not None:
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
    add_user(user_obj)



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
    user = get_user_by_query({
        "email": email
    })
    if user is None:
        raise ValueError("Incorrect email/password.")

    user_password = user["password"]
    if not bcrypt.checkpw(password.encode(), user_password):
        raise ValueError("Incorrect email/password.")

    return user

def get_user_by_id(u_id: str) -> ReturnDocument:
    return get_user_by_query({
        "_id": u_id
    })

def update_user(u_id: str, data: Dict[str, Any]) -> None:
    update_user_by_query({
        "_id": u_id
    }, data)
