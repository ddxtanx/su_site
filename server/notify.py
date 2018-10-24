from skyward_api import SkywardAPI, Assignment, SkywardError, SessionError, SkywardClass
from pymongo import MongoClient
from pymongo.collection import ReturnDocument, Collection
from typing import Any, Dict, List, Tuple
import smtplib
from time import sleep
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import environ
from pickle import dumps, loads
if __name__ == "__main__":
    import users
else:
    import server.users as users
#####

def wait_for(sec: int, interval: float = .1) -> None:
    for i in range(0, int(sec/interval)):
        sleep(interval)

def login_to_server():
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.connect("smtp.gmail.com", 587)
    try:
        server.ehlo()
        server.starttls()
        server.ehlo()
    except smtplib.SMTPNotSupportedError:
        pass
    server.login(environ["email"], environ["email_pass"])
    return server
#####
GradeList = Dict[str, List[Assignment]]

def find_diff(u_id: str) -> Tuple[List[SkywardClass], List[SkywardClass]]:
    user_obj = users.get_user_by_id(u_id)
    mongo_grades_pkl = user_obj["grades"]
    mongo_grades = loads(mongo_grades_pkl)
    sky_data = user_obj["sky_data"]
    service = user_obj["service"]
    if sky_data == {}:
        return (None, None)
    curr_grades = SkywardAPI.from_session_data(service, sky_data).get_grades()
    users.update_user(u_id, {"grades": dumps(curr_grades)})
    changed_grades = [] # type: List[SkywardClass]
    removed_grades = [] # type: List[SkywardClass]
    for curr_class, old_class in zip(curr_grades, mongo_grades):
        changed_grades.append(curr_class - old_class)
        removed_grades.append(old_class - curr_class)
    return (changed_grades, removed_grades)

def send_email(
    email: str,
    added: List[SkywardClass],
    removed: List[SkywardClass]
) -> None:
    changes_text = {}
    changes_html = {}
    for sky_class in added:
        class_name = sky_class.name
        grade_changes = sky_class.grades
        change_str_text = ""
        change_str_html = ""
        for change in grade_changes:
            assignment_name = change.name
            assignment_grade = change.letter_grade
            if assignment_grade != "*":
                change_str_html += "\t<li>The grade for {0} was changed to {1}</li>\n".format(
                    assignment_name,
                    change.points_str()
                )
                change_str_text += "\tThe grade for {0} was changed to {1}\n".format(
                    assignment_name,
                    change.points_str()
                )
            else:
                change_str_html += "\t<li>{0} was added to the gradebook</li>\n".format(
                    assignment_name
                )
                change_str_text += "\t<li>{0} was added to the gradebook</li>\n".format(
                    assignment_name
                )
        if change_str_text != "":
            changes_text[class_name] = change_str_text
            changes_html[class_name] = change_str_html
    for sky_class in removed:
        class_name = sky_class.name
        grade_changes = sky_class.grades
        change_str_text = ""
        change_str_html = ""
        for change in grade_changes:
            change_str_text = "\t{0} was removed from the gradebook\n".format(change.name)
            change_str_html = "<li>{0} was removed from the gradebook</li>".format(change.name)
        if change_str_text != "":
            changes_text[class_name] += change_str_text
            changes_html[class_name] += change_str_html
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
        msg['From'] = environ["email"]
        msg['To'] = email

        msg.attach(MIMEText(email_str_text, "plain"))
        msg.attach(MIMEText(email_str_html, "html"))

        server = login_to_server()
        server.sendmail(email, email, msg.as_string())

def handle_session_error(u_id: str, email: str):
  users.update_user(u_id, {
      "sky_data": {}
  })
  server = login_to_server()
  message_text = (
      "Your session has been destroyed. "
      "Please retry your login at "
      "{0}/profile. "
      "Thank you! \n\n"
      "--Skyward Updater".format(environ["url"])
  )
  message_html = (
      "<p>"
      "Your session has been destroyed. "
      "Please retry your login "
      "<a href=\"{0}/profile\"> here. </a>"
      "Thank you!"
      "</p><br/><br/>"
      "--Skyward Updater".format(environ["url"])
  )
  msg = MIMEMultipart('alternative')
  msg['Subject'] = "Session destroyed! :("
  msg['From'] = environ["email"]
  msg['To'] = email

  msg.attach(MIMEText(message_text, "plain"))
  msg.attach(MIMEText(message_html, "html"))

  server.sendmail(environ["email"], email, msg.as_string())

def notify(notify) -> None:
    u_id = notify["_id"]
    email = notify["email"]
    if notify["sky_data"] == {}:
        return
    added, removed= find_diff(u_id)
    send_email(email, added, removed)

def keep_alive(notify) -> None:
    sky_data = notify["sky_data"]
    if sky_data == {}:
        return

    service = notify["service"]
    user_api = SkywardAPI.from_session_data(service, sky_data)
    user_api.keep_alive()

def main() -> None:
    mins = 0
    while True:
        notify_users = users.get_users()
        for user in notify_users:
            try:
                keep_alive(user)
                if mins == 0:
                    notify(user)
            except SessionError:
                handle_session_error(user["_id"], user["email"])
            except SkywardError:
                wait_for(30)
        mins = (mins + 1) % 5
        wait_for(3*60)
if __name__ == "__main__":
    main()
