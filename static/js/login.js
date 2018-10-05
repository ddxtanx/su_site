/*
    global location
    global $
    global io
*/

function SocCreator(url){
    return io.connect('http://' + document.domain + ':' + location.port + '/' + url);
}

$(document).ready(function(){
    var soc = SocCreator("soc/login");
    $("#submit").click(function(){
        console.log("Logging in.")
        soc.emit("login", {
            data: {
                "username": $("#username").val(),
                "password": $("#password").val()
            }
        })
    })
    
    soc.on("grades", function(message){
        console.log("ASD")
        console.log(message.data)
    })
    
    soc.on("error", function(message){
        if(message.data["error"] === "login"){
            console.log("Try again!")
        }
    })
})

