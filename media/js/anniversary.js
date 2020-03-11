/* cookie util functions from https://www.w3schools.com/js/js_cookies.asp */

function setCookie(cname, cvalue, exdays) {
  var d = new Date();
  d.setTime(d.getTime() + (exdays*24*60*60*1000));
  var expires = "expires="+ d.toUTCString();
  document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

function getCookie(cname) {
  var name = cname + "=";
  var decodedCookie = decodeURIComponent(document.cookie);
  var ca = decodedCookie.split(';');
  for(var i = 0; i <ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}

/* functions to show anniversary easter eggs */

function set_anniversary_logo(){
  var logo = document.getElementById('logo');
  logo.style.backgroundImage  = 'url(/media/images/logo_anniversary.png)';
  logo.style.width = '320px';
  logo.style.height = '72px';
}

function show_balloons_animation(){
  var balloonsElement = document.createElement("div");
  balloonsElement.id = "balloons";
  for (var i=0; i<5; i++){
    var balloon = document.createElement("div");
    balloon.className = 'balloon';
    balloonsElement.appendChild(balloon);
  }
  document.body.appendChild(balloonsElement);
}

function show_anniversary_easter_egg(){
  if (getCookie('anniversaryAnimation') === ''){
    show_balloons_animation();
    setTimeout(function(){
      set_anniversary_logo();
    },3200);
    setCookie('anniversaryAnimation', 'seen', 20);
  } else {
    set_anniversary_logo();
  }
}

window.addEventListener("load", function(){
    show_anniversary_easter_egg();
});