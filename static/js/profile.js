/*
  global $
  global io
  global location
*/
function SocCreator(url){
    return io.connect(location.host + '/' + url)
}
var normal_soc = SocCreator("soc/sky_login");
var task_soc = SocCreator("soc/tasks");
var task_id;
var interval;

normal_soc.on("success", function(message){
  task_id = message.data.t_id;
  interval = setInterval(check_task, 1000);
})
function check_task(){
  task_soc.emit("check login task", {
    "data": {
      "t_id": task_id
    }
  });
}


$(document).ready(function(){
  $("#notify").hide()

  $("#sky_form").on("submit", function(){
    var uname = $("#sky_name").val()
    var upass = $("#sky_pass").val()
    var serv = $("#service").val()
    normal_soc.emit("login", { data:{
      "username": uname,
      "password": upass,
      "service": serv
    }});
    $("#notify").text("Logging in...")
    $("#notify").show()
    return false;
  })
  task_soc.on("not ready", function(){
    var notif_text = $("#notify").text()
    var num_of_dots = (notif_text.match(/\./g) || []).length
    console.log(num_of_dots)
    var new_num_of_dots = (num_of_dots + 1) % 4
    console.log(new_num_of_dots)
    var dots_str = ".".repeat(new_num_of_dots)
    $("#notify").text("Logging in" + dots_str)
  })

  task_soc.on("ready", function(message){
    window.clearInterval(interval)
    var data = message.data;
    if(data.status === "good"){
      $("#notify").text("Succsessfully logged in!");
      $(".hsd").css("display", "inline");
    } else if(data.status === "incorrect"){
      $("#sky_name").val("")
      $("#sky_pass").val("")
      $("#notify").text("Username/Password/Service incorrect...")
    } else{
      $("#notify").text("Oof, something went wrong...")
    }
  })

});

$(window).on("beforeunload", function(){
  if(task_id != undefined){
    task_soc.emit("cancel", {
      "data": {
        "t_id": task_id
      }
    })
    window.clearInterval(interval)
  }
})
