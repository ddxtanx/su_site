from flask import Flask, url_for, render_template, request, redirect
from skyward_api import SkywardAPI, Assignment, SessionError, SkywardError, SkywardClass
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_socketio import SocketIO, emit
from typing import Dict, Any, List
import server.users as users
from server.users import User
import os
from pickle import loads, dumps

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["key"]
socket = SocketIO(app)

#####
GradeList = Dict[str, List[Assignment]]
#####
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(u_id: str):
    return User.from_id(u_id)

@login_manager.unauthorized_handler
def unauth():
    return redirect("/login?error=not_logged_in")

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
        data["logged_in"] = current_user.is_authenticated()
        data["hsd"] = current_user.sky_data != {}
        data["u_id"] = current_user.id

    return data

@app.route("/")
def hello():
    return render_template("default.html.j2", **page_data("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    data = page_data("login")
    data["error"] = ""
    if request.method == "POST":
        try:
            email = request.form["email"]
            password = request.form["password"]
            user = User.from_login(email, password)
            login_user(user)
            data["logged_in"] = True
        except ValueError as e:
            if "Incorrect" in str(e):
                data["error"] = "u/p"
            elif "logged in" in str(e):
                data["error"] = "logged"
    data.update(request.args.to_dict())
    return render_template("login.html.j2", **data)

@app.route("/register", methods=["GET", "POST"])
def register():
    data = page_data("register")
    data["error"] = ""
    if request.method == "POST":
        if current_user.is_authenticated():
            data["error"] = "logged"
        else:
            email = request.form["email"]
            p1 = request.form["password1"]
            p2 = request.form["password2"]
            try:
                users.register(email, p1, p2)
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

@socket.on("login", namespace="/soc/sky_login")
def sky_login(message):
    username = message["data"]["username"]
    password = message["data"]["password"]
    service = message["data"]["service"]
    try:
        api = SkywardAPI(service)
        api.setup(username, password)
        sess_data = api.get_session_params()
        current_user.set_sky_data(sess_data)
        current_user.set_service(service)
        emit("login resp", {
            "data":{
                "status": "good"
            }
        })
    except ValueError:
        emit("login resp", {
            "data":{
                "status": "incorrect"
            }
        })
    except SkywardError as e:
        emit("login resp", {
            "data":{
                "status": "skyward"
            }
        })

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
    data = page_data("grades")
    return render_template("grades.html.j2", **data)


def manual_grade_retrieve(u_id: str) -> List[SkywardClass]:
    sky_data = current_user.sky_data
    api = SkywardAPI.from_session_data(current_user.service, sky_data, timeout=30)
    grades = api.get_grades()
    return grades

@socket.on("get grades", namespace="/soc/grades")
def get_grades(message):
    u_id = message["data"]["u_id"]
    try:
        grades = [] # type: List[SkywardClass]
        try:
            if "force" not in message["data"]:
                grades = current_user.grades
            else:
                grades = manual_grade_retrieve(u_id)
                current_user.set_grades(grades)
        except (TypeError, KeyError):
            grades = manual_grade_retrieve(u_id)
            current_user.set_grades(grades)
        grades_text = {}
        for sky_class in grades:
            grades_text[sky_class.name] = sky_class.grades_to_text()
        emit("grades", {
            "data": grades_text
        })
    except SessionError as e:
        current_user.set_sky_data({})
        emit("error")
        return

if __name__=="__main__":
    socket.run(app, host=os.environ["HOST"], port=int(os.environ["PORT"]))
