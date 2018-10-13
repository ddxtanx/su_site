/*
  global $
  global io
  global location
*/
function SocCreator(url){
    return io.connect(location.host + '/' + url);
}

$(document).ready(function(){
  $("#notify").hide()
  var soc = SocCreator("soc/sky_login");
  $("#submit").click(function(){
    var uname = $("#sky_name").val()
    var upass = $("#sky_pass").val()
    var serv = $("#service").val()
    soc.emit("login", { data:{
      "username": uname,
      "password": upass,
      "service": serv
    }});
    $("#notify").show()
  });

  soc.on("login resp", function(message){
    var data = message.data;
    if(data.status === "good"){
      $("#notify").text("Succsessfully logged in!");
      $("#grades_link").css("display", "inline");
      $("#notifier_link").css("display", "inline");
    } else if(data.status === "incorrect"){
      $("#sky_name").val("")
      $("#sky_pass").val("")
      $("#notify").text("Username/Password/Service incorrect...")
    } else{
      $("#notify").text("Oof, something went wrong...")
    }
  })

})
