from pymongo import MongoClient
from os import environ

client = MongoClient("mongodb://{0}:{1}@ds223653.mlab.com:23653/updater".format(
        environ["db_user"],
        environ["db_pass"]
))