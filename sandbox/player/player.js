soundManager.debugMode = false;
  
soundManager.onload = function() {
    console.profile()
    $$('div.preview').each(initPlayer);
    console.profileEnd();
};

// when soundmanager fails to insert the flash player, just show the preview links
// this also helps visually impaired users!
soundManager.onerror = function () {
    $$('a.preview-mp3').each( function (element) {
        element.title = "No-flash preview (need flash 9.0.100 minmal installed))";
        element.show();
    } );
    $$('div.play-controls').each( Element.hide );
    $$('div.progress-container').each( Element.hide );
};

function msToTime(ms)
{
    var s = parseInt(ms / 1000);
    var seconds = s % 60;
    var minutes = parseInt(s / 60);
    if (seconds < 10)
        seconds = '0' + seconds;
    else
        seconds = '' + seconds;

    if (minutes < 10)
        minutes = '0' + minutes;
    else
        minutes = '' + minutes;

    return minutes + ':' + seconds;
}

var sndCounter = 0;

function initPlayer(element)
{
    var children = element.childNodes;
    var progressContainer = children[3];
        var pcChildren = progressContainer.childNodes;
        var loaded = pcChildren[1];
        var position = pcChildren[3];
    var playControls = children[5];
        var cChildren = playControls.childNodes;
        var rewind = cChildren[1];
        var play = cChildren[3];
        var loop = cChildren[5];
        var timeDisplay = cChildren[7];
    var url = children[7];

    /*
    var url = element.down("a.preview-mp3");
    var progressContainer = element.down("div.progress-container");
    var position = element.down("div.position");
    var loaded = element.down("div.loaded");
    var rewind = element.down("div.rewind");
    var play = element.down("div.play");
    var loop = element.down("div.loop");
    var timeDisplay = element.down("div.time-display");
    */

    url = url.href;

    var updateTimeDisplay = function (ms) {
        var newTime = msToTime(ms);
        if (timeDisplay.innerHTML != newTime)
            timeDisplay.update(newTime);
    };

    var sound = soundManager.createSound({
        id: 'snd' + (sndCounter++),
        url: url,
        onfinish: function () {
            if (loop.hasClassName("on"))
            {
                sound.play();
            }
            else
            {
                play.removeClassName("on");
                updateTimeDisplay(0);
                position.style.width = 0;
            }
        },
        whileplaying: function () {
            position.style.width = parseInt(((100.0*sound.position)/sound.durationEstimate)) + "%";
            updateTimeDisplay(sound.position);
        },
        whileloading: function () {
            loaded.style.width = parseInt(((100.0*sound.bytesLoaded)/sound.bytesTotal)) + "%";
        },
    });
    
    progressContainer.observe('click', function (event) {
        var click = (event.pointerX() - progressContainer.cumulativeOffset()[0])
        var time = (click * sound.durationEstimate) / progressContainer.getWidth();
        
        if (time > sound.duration)
            time = sound.duration * 0.95;
        
        sound.setPosition(time);
    });

    rewind.observe('click', function (event)
    {
        sound.setPosition(0);
        updateTimeDisplay(0);
        position.style.width = 0;
    });
    rewind.observe('mousedown', function (event) { rewind.addClassName('on'); });
    rewind.observe('mouseup', function (event) { rewind.removeClassName('on'); });
    
    play.observe('click', function (event)
    {
        sound.togglePause();
        play.toggleClassName("on");
    });
    
    loop.observe('click', function (event) { loop.toggleClassName('on'); });
}
