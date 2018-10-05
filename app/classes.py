from typing import Dict
from validate_email import validate_email
from pymongo.collection import Collection

class Schema():
    def write(self, collect: Collection):
        collect.insert_one(self.__dict__)
        
        

class User(Schema):
    def __init__(
        self,
        username: str,
        password: str,
        email: str,
        sky_data: Dict[str, str]
    ):
        self.username = username
        self.password = password
        if validate_email(email):
            self.email = email
            self.sky_data = sky_data
        else:
            raise ValueError("Email must be a valid email.")
    
    
        
        