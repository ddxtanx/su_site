from flask import Flask, url_for, render_template, request
from skyward_api import SkywardAPI
from flask_socketio import SocketIO, emit
from typing import Dict
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["key"]
socket = SocketIO(app)
def css_js_url(name: str) -> Dict[str, str]:
    return {
        "css_link": url_for("static", filename="/css/{0}.css".format(name)).replace("//", "/"),
        "js_link": url_for("static", filename="/js/{0}.js".format(name)).replace("//", "/"),
        "name": name
    }

@app.route("/")
def hello():
    return render_template("default.html", **css_js_url("index"))
    
@app.route("/login")
def login():
    return render_template("login.html", **css_js_url("login"))
    
@socket.on("init", namespace="/soc/echo")
def echo_socket(message):
    data = message["data"]
    print(str(data))
    emit(data)

@socket.on("login", namespace="/soc/login")
def socket_login(message):
    print(message)
    data = message["data"]
    username = data["username"]
    passw = data["password"]
    try:
        api = SkywardAPI(username, passw, "wseduoakparkrfil")
        grades = api.get_grades_text()
        emit("grades", {"data": grades}, namespace="/soc/login")
        print("Sent grades")
    except ValueError:
        emit("error", {"data": {"error": "login"}})

if __name__ == "__main__":
    socket.run(app, host="0.0.0.0", port=8080)