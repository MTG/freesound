// For AJAX posts

$(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

// For ajax get (as a substitute to GDownloadUrl from googlemaps)
function ajaxLoad(url,callback,postData,plain) {
    var http_request = false;

    if (window.XMLHttpRequest) { // Mozilla, Safari, ...
        http_request = new XMLHttpRequest();
        if (http_request.overrideMimeType && plain) {
            http_request.overrideMimeType('text/plain');
        }
    } else if (window.ActiveXObject) { // IE
        try {
            http_request = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {
            try {
                http_request = new ActiveXObject("Microsoft.XMLHTTP");
            } catch (e) {}
        }
    }
    if (!http_request) {
        //alert('Giving up :( Cannot create an XMLHTTP instance');
        console.log('Giving up :( Cannot create an XMLHTTP instance');
        return false;
    }
    http_request.onreadystatechange =  function() {
        if (http_request.readyState == 4) {
            if (http_request.status == 200) {
                eval(callback(http_request));
            }
            else {
                //alert('Request Failed: ' + http_request.status);
                conosle.log('Request Failed: ' + http_request.status);
            }
        }
    };

    if (postData) { // POST
        http_request.open('POST', url, true);
        http_request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        http_request.setRequestHeader("Content-length", postData.length);
        http_request.send(postData);
    }
    else {
        http_request.open('GET', url, true);
        http_request.send(null);
    }
}

