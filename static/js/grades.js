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
var soc = SocCreator("soc/grades");

function get_grades(){
  soc.emit("get grades", {
    "data": {
      "u_id": u_id
    }
  })
}
$(document).ready(function(){
  soc.on("grades", function(message){
    $("#notify").hide();
    grades = message.data;
    var p_num = 1;
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
  });

  soc.on("error", function(){
    window.location.href="/profile?error=destroyed";
  })
  $("#force").click(function(){
    $("#grades").empty()
    $("#notify").show()
    soc.emit("get grades", {
      "data": {
        "u_id": u_id,
        "force": true
      }
    })
  })
});

$(window).unload(function(){
  soc.emit("cancel grades", {
    "data": {
      "u_id": u_id
    }
  })
})
