from skyward_api import SkywardAPI
from pymongo import MongoClient
from pymongo.collection import ReturnDocument, Collection
from typing import Any, Dict, List, Tuple
import smtplib
from time import sleep
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import environ

#####
def points_str(dict: Dict[str, str]) -> str:
    return "{0}/{1} ({2})".format(
            dict["num_points"],
            dict["total_points"],
            dict["letter_grade"]
        )
#####
GradeList = Dict[str, List[Dict[str, str]]]

def get_diff(new_grades: GradeList, old_grades: GradeList) -> GradeList:
    difference = {} #type: Dict[str, List[Dict[str, str]]]

    for class_name in new_grades.keys():
        if class_name in old_grades.keys():
            new_grade_list = new_grades[class_name]
            old_grade_list = old_grades[class_name]
            diff = [
                item
                for item in new_grade_list if item not in old_grade_list
            ]
            difference[class_name] = diff
    return difference

def find_diff(u_id: str, nc: Collection) -> Tuple[GradeList, GradeList]:
    notify_obj = nc.find_one({
        "_id": u_id
    })
    mongo_grades = notify_obj["grades"]
    sky_data = notify_obj["sky_data"]
    service = notify_obj["service"]
    curr_grades = SkywardAPI.from_session_data(service, sky_data).get_grades_json()
    update_record(u_id, {"grades": curr_grades})
    changed_grades = get_diff(curr_grades, mongo_grades)
    removed_grades = get_diff(mongo_grades, curr_grades)
    return (changed_grades, removed_grades)

def send_email(
    email: str,
    added: GradeList,
    removed: GradeList
) -> None:
    changes_text = {}
    changes_html = {}
    for clas, grade_changes in added.items():
        change_str_text = ""
        change_str_html = ""
        for change in grade_changes:
            assignment_name = change["name"]
            assignment_grade = change["letter_grade"]
            if assignment_grade != "*":
                change_str_html += "\t<li>The grade for {0} was changed to {1}</li>\n".format(
                    assignment_name,
                    points_str(change)
                )
                change_str_text += "\tThe grade for {0} was changed to {1}\n".format(
                    assignment_name,
                    points_str(change)
                )
            else:
                change_str_html += "\t<li>{0} was added to the gradebook</li>\n".format(
                    assignment_name
                )
                change_str_text += "\t<li>{0} was added to the gradebook</li>\n".format(
                    assignment_name
                )
        if change_str_text != "":
            changes_text[clas] = change_str_text
            changes_html[clas] = change_str_html
    for clas, grade_removed in removed.items():
        change_str_text = ""
        change_str_html = ""
        for change in grade_changes:
            change_str_text = "\t{0} was removed from the gradebook\n".format(change["name"])
            change_str_html = "<li>{0} was removed from the gradebook</li>".format(change["name"])
        if change_str_text != "":
            changes_text[clas] += change_str_text
            changes_html[clas] += change_str_html
    if changes_text != {}:
        email_str_html = ""
        for key, value in changes_html.items():
            if value != "":
                email_str_html += "<ul> <h2>In {0}</h2>\n {1}</ul>".format(key, value)
        email_str_text = ""
        for key, value in changes_text.items():
            if value != "":
                email_str_text += "In {0}\n {1}".format(key, value)
        email_str_text += "\n You can view all your grades at {0}/grades".format(environ["url"])
        email_str_html += "<h2> You can view all your grades <a href='{0}/grades'>here.</a> </h2>".format(environ["url"])
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Gradebook Update!"
        msg['From'] = email
        msg['To'] = email

        msg.attach(MIMEText(email_str_text, "plain"))
        msg.attach(MIMEText(email_str_html, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.connect("smtp.gmail.com", 587)
        try:
            server.ehlo()
            server.starttls()
            server.ehlo()
        except smtplib.SMTPNotSupportedError:
            pass
        server.login(environ["email"], environ["email_pass"])
        server.sendmail(email, email, msg.as_string())

def loop_and_notify(nc: Collection) -> None:
    notifs = nc.find({})
    for notify in notifs:
        email = notify["email"]
        u_id = notify["_id"]
        added, removed= find_diff(u_id, nc)
        send_email(email, added, removed)

def main() -> None:
    client = MongoClient("mongodb://{0}:{1}@ds223653.mlab.com:23653/updater".format(
            environ["db_user"],
            environ["db_pass"]
    ))
    db = client["updater"]
    notify_collect = db["notify"]
    while True:
        loop_and_notify(notify_collect)
        sleep(4*60)

def get_record(u_id: str) -> ReturnDocument:
    client = MongoClient("mongodb://{0}:{1}@ds223653.mlab.com:23653/updater".format(
            environ["db_user"],
            environ["db_pass"]
    ))
    db = client["updater"]
    notify_collect = db["notify"]
    return notify_collect.find_one({"_id": u_id})

def update_record(u_id: str, data: Dict[str, Any]) -> None:
    client = MongoClient("mongodb://{0}:{1}@ds223653.mlab.com:23653/updater".format(
            environ["db_user"],
            environ["db_pass"]
    ))
    db = client["updater"]
    notify_collect = db["notify"]
    notify_collect.update_one({"_id": u_id}, {
        "$set": data
    })


if __name__ == "__main__":
    main()
