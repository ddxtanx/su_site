from flask import Flask, url_for, render_template, request, redirect
from skyward_api import SessionError, SkywardError, SkywardClass
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_socketio import SocketIO, emit
from server.tasks import login_task, get_grades_task
from server.tasks import app as celery_app
from typing import Dict, Any, List
import server.users as users
from server.users import make_id
from server.users import User
import os
from celery.result import AsyncResult
from celery.task.control import revoke
from pickle import loads, dumps
from flask_sslify import SSLify


app = Flask(__name__)
app.debug = os.environ["debugging"] if "debugging" in os.environ else False
ssl = SSLify(app)
app.config["SECRET_KEY"] = os.environ["key"]
socket = SocketIO(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(u_id: str) -> User:
    return User.from_id(u_id)

@login_manager.unauthorized_handler
def unauth():
    return redirect("/login?error=not_logged_in")

def manual_grade_retrieve_task(
    sky_data: Dict[str, str],
    service: str
) -> None:
    results = get_grades_task.delay(service, sky_data)
    emit("success", {
        "data": {
            "t_id": results.task_id
        }
    })

def page_data(name: str) -> Dict[str, Any]:
    data = {
        "css_link": url_for("static", filename="/css/{0}.css".format(name)).replace("//", "/"),
        "js_link": url_for("static", filename="/js/{0}.js".format(name)).replace("//", "/"),
        "name": name,
        "logged_in": False,
        "hsd": False,
        "u_id": "",
        "default_css_link": url_for("static", filename="/css/sidebar.css").replace("//", "/")
    }
    if current_user.is_authenticated:
        current_user.sky_data = users.get_user_by_id(current_user.id)["sky_data"]
        data["logged_in"] = current_user.is_authenticated
        data["hsd"] = current_user.sky_data != {}
        data["u_id"] = current_user.id

    return data

@app.route("/")
def hello():
    return render_template("default.html.j2", **page_data("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    data = {} # type: Dict[str, Any]
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.from_login(email, password)
        if user is None:
            data["error"] = "u/p"
        elif current_user.is_authenticated:
            data["error"] = "logged"
        else:
            login_user(user)
            data["logged_in"] = True
    data.update(page_data("login"))
    data.update(request.args.to_dict())
    return render_template("login.html.j2", **data)

@app.route("/register", methods=["GET", "POST"])
def register():
    data = page_data("register")
    data["error"] = ""
    if request.method == "POST":
        if current_user.is_authenticated:
            data["error"] = "logged"
        else:
            email = request.form["email"]
            p1 = request.form["password1"]
            p2 = request.form["password2"]
            try:
                users.register(email, p1, p2)
                data["error"] = "none"
            except ValueError as e:
                if "must be the same" in str(e):
                    data["error"] = "same"
                elif "valid" in str(e):
                    data["error"] = "valid"
                elif "already used" in str(e):
                    data["error"] = "used"
    return render_template("register.html.j2", **data)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/profile")
@login_required
def profile():
    data = page_data("profile")
    data.update(request.args.to_dict())
    data["service"] = current_user.service
    return render_template("profile.html.j2", **data)

@app.route("/grades")
@login_required
def grades():
    if not current_user.is_active():
        return redirect("/profile?error=no_data")
    data = page_data("grades")
    return render_template("grades.html.j2", **data)

@app.route("/skyward")
@login_required
def skyward_page():
    if not current_user.is_active():
        return redirect("/profile?error=no_data")
    data = page_data("skyward")
    data.update(current_user.sky_data)
    data["url"] = "https://skyward.iscorp.com/scripts/wsisa.dll/WService={0}/sfhome01.w".format(current_user.service)
    return render_template("skyward.html.j2", **data)

@socket.on("login", namespace="/soc/sky_login")
def sky_login(message):
    username = message["data"]["username"]
    password = message["data"]["password"]
    service = message["data"]["service"]
    u_id = current_user.id
    sess_data_results = login_task.delay(username, password, service)
    emit("success", {
        "data":{
            "t_id": sess_data_results.task_id
        }
    })

@socket.on("get grades", namespace="/soc/grades")
def get_grades(message):
    sky_data = current_user.sky_data
    service = current_user.service
    try:
        grades = [] # type: List[SkywardClass]
        try:
            if "force" not in message["data"]:
                grades = current_user.grades
            else:
                manual_grade_retrieve_task(sky_data, service)
                return
        except (TypeError, KeyError):
            manual_grade_retrieve_task(sky_data, service)
            return
        grades_text = {}
        for sky_class in grades:
            grades_text[sky_class.skyward_title()] = sky_class.grades_to_text()
        emit("grades", {
            "data": grades_text
        })
    except SessionError as e:
        current_user.set_sky_data({})
        emit("error")
        return

@socket.on("check grades task", namespace="/soc/tasks")
def check_grades_task(message):
    def process_grades(grades: List[SkywardClass]) -> None:
        current_user.set_grades(grades)
        text_grades = {}
        for sky_class in grades:
            text_grades[sky_class.skyward_title()] = sky_class.grades_to_text()
        emit("ready", {
            "data": text_grades
        })
    check_task(message, process_grades)

@socket.on("check login task", namespace="/soc/tasks")
def check_login_task(message):
    def process_sky_data(sky_data: Dict[str, str]) -> None:
        if "error" in sky_data:
            emit("ready", {
                "data": {
                    "status": "incorrect"
                }
            })
            return
        current_user.set_sky_data(sky_data)
        emit("ready", {
            "data": {
                "status": "good"
            }
        })
    check_task(message, process_sky_data)
def check_task(message, fn):
    t_id = message["data"]["t_id"]
    task = AsyncResult(id=t_id, app=celery_app)
    try:
        if task.ready():
            result = task.get()
            fn(result)
        else:
            emit("not ready")
    except SkywardError:
        current_user.set_sky_data({})
        emit("error")
    except ValueError:
        emit("ready", {
            "data": "incorrect"
        })

@socket.on("cancel", namespace="/soc/tasks")
def cancel_task(message):
    t_id = message["data"]["t_id"]
    task = AsyncResult(id=t_id, app=celery_app)
    task.revoke(terminate=True, signal='SIGKILL')
    emit("cancel success")


if __name__=="__main__":
    socket.run(app, host=os.environ["HOST"], port=int(os.environ["PORT"]))
