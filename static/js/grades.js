/*
  global $
  global io
  global location
  global window
  global u_id
*/
function SocCreator(url){
    return io.connect(location.host + '/' + url);
}
var normal_soc = SocCreator("soc/grades");
var task_soc = SocCreator("soc/tasks");
var task_id;
var interval;

function get_grades(){
  normal_soc.emit("get grades", {
    "data": {
      "u_id": u_id
    }
  })
}
function check_task(){
  task_soc.emit("check grades task", {
    "data": {
      "t_id": task_id
    }
  });
}

task_soc.on("ready", function(message){
  grades = message.data
  write_grades(grades)
  window.clearInterval(interval)
})


normal_soc.on("success", function(message){
  task_id = message.data.t_id;
  interval = setInterval(check_task, 1000)
})

function write_grades(grades){
  var p_num = 1;
  $("#notify").hide();
  Object.keys(grades).forEach(function(class_name){
    var class_grades = grades[class_name];
    var class_div = $("<div>", {
      id: `P${p_num}`,
      class: "grades"
    });
    p_num++;
    $("#grades").append(class_div)
    class_div.append($("<p>", {text: class_name}))
    var list = $("<ul>")
    class_div.append(list)
    for(var x = 0; x<class_grades.length; x++){
      list.append($("<li>", {text: class_grades[x]}))
    }
  });
}
$(document).ready(function(){
  normal_soc.on("grades", function(message){
    grades = message.data;
    write_grades(grades)
  });

  task_soc.on("error", function(){
    window.location.href="/profile?error=destroyed";
  })
  $("#force").click(function(){
    $("#grades").empty()
    $("#notify").show()
    normal_soc.emit("get grades", {
      "data": {
        "force": true
      }
    })
  })
});
