from flask import Flask, url_for, render_template, request, session, redirect
from skyward_api import SkywardAPI, Assignment
from flask_socketio import SocketIO, emit
from typing import Dict, Any, List
import server.users as users
import os
from pickle import loads, dumps

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["key"]
socket = SocketIO(app)

#####
GradeList = Dict[str, List[Assignment]]
#####

def page_data(name: str) -> Dict[str, Any]:
    try:
        session["sky_data"] = users.get_user_by_id(session["id"])["sky_data"]
    except KeyError:
        pass
    log_in = "logged_in" in session.keys() and session["logged_in"]
    has_sky_data = "sky_data" in session and session["sky_data"] != {}
    u_id = session["id"] if "id" in session else ""
    data = {
        "css_link": url_for("static", filename="/css/{0}.css".format(name)).replace("//", "/"),
        "js_link": url_for("static", filename="/js/{0}.js".format(name)).replace("//", "/"),
        "name": name,
        "logged_in": log_in,
        "hsd": has_sky_data,
        "u_id": u_id,
        "default_css_link": url_for("static", filename="/css/sidebar.css").replace("//", "/")
    }
    return data

@app.route("/")
def hello():
    data = page_data("index")
    return render_template("default.html.j2", **data)

@app.route("/login", methods=["GET", "POST"])
def login():
    data = page_data("login")
    data["error"] = ""
    if request.method == "POST":
        try:
            email = request.form["email"]
            password = request.form["password"]
            user = users.login(email, password)
            u_id = user["_id"]
            sky_data = user["sky_data"]
            service = user["service"]
            session["id"] = u_id
            session["sky_data"] = sky_data
            session["service"] = service
            session["logged_in"] = True
            data["logged_in"] = True
        except ValueError as e:
            if "Incorrect" in str(e):
                data["error"] = "u/p"
            elif "logged in" in str(e):
                data["error"] = "logged"
    print(data)
    return render_template("login.html.j2", **data)

@app.route("/register", methods=["GET", "POST"])
def register():
    data = page_data("register")
    data["error"] = ""
    if request.method == "POST":
        if "id" in session.keys():
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
def logout():
    session.clear()
    return redirect("/")

@socket.on("login", namespace="/soc/sky_login")
def sky_login(message):
    print("Got login.")
    username = message["data"]["username"]
    password = message["data"]["password"]
    service = message["data"]["service"]
    try:
        api = SkywardAPI(service)
        api.setup(username, password)
        sess_data = api.get_session_params()
        users.update_user(session["id"], {
            "sky_data": sess_data,
            "service": service
        })
        session["sky_data"] = sess_data
        session["service"] = service
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
    except RuntimeError:
        emit("login resp", {
            "data":{
                "status": "skyward"
            }
        })

@app.route("/profile")
def profile():
    data = page_data("profile")
    data.update(request.args.to_dict())
    if "service" in session:
        data["service"] = session["service"]
    else:
        data["service"] = ""
    print(data)
    return render_template("profile.html.j2", **data)

@app.route("/grades")
def grades():
    data = page_data("grades")
    return render_template("grades.html.j2", **data)

@socket.on("get grades", namespace="/soc/grades")
def get_grades(message):
    u_id = message["data"]["u_id"]
    try:
        grades = {}
        try:
            grades = loads(users.get_user_by_id(u_id)["grades"])
        except (TypeError, KeyError):
            user = users.get_user_by_id(u_id)
            sky_data = user["sky_data"]
            api = SkywardAPI.from_session_data(user["service"], sky_data)
            grades = api.get_grades()
            users.update_user(u_id, {
                "grades": dumps(grades)
            })
        grades_text = {}
        for key, item in grades.items():
            grades_text[key] = list(
                map(
                    lambda grade: str(grade),
                    item
                )
            )
        emit("grades", {
            "data": grades_text
        })
        print("Sent grades")
    except RuntimeError as e:
        print(str(e))
        users.update_user(session["id"], {"sky_data": {}})
        emit("error")
        return

if __name__=="__main__":
    socket.run(app, host=os.environ["HOST"], port=int(os.environ["PORT"]))
