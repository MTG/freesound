
soundManager.debugMode = false;

Event.observe(window, 'load', function() {
    console.time("onload");
});
  
soundManager.onload = function() {
    console.timeEnd("onload");
    console.time("parsing");
    $$('div.preview').each(initPlayer);
    console.timeEnd("parsing");
};

// when soundmanager fails to insert the flash player, just show the preview links
// this also helps visually impaired users!
soundManager.onerror = function () {
    $$('a.preview-mp3').each( function (element) { element.insert('<br />').show(); } );
    $$('div.play-controls').each( Element.hide );
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
    var url = element.down("a.preview-mp3").href;
    var progressContainer = element.down("div.progress-container");
    var progress = element.down("div.progress");
    var play = element.down("div.play");
    var loop = element.down("div.loop");
    var timeDisplay = element.down("div.time-display");

    if (timeDisplay)
        updateTimeDisplay = function (ms) { timeDisplay.update(msToTime(ms)) };
    else
        updateTImeDisplay = function (ms) {};

    var sound = soundManager.createSound({id: 'snd' + (sndCounter++), url: url, onfinish: function () {
        if (loop.hasClassName("on"))
            sound.play();
        else
        {
            play.removeClassName("on");
            updateTimeDisplay(0);
            progress.style.width = 0;
        }
    }, whileplaying : function () {
        progress.style.width = ((100.0*sound.position)/sound.durationEstimate) + "%";
        updateTimeDisplay(sound.position);
    }});
    
    progressContainer.observe('click', function (event) {
        if (!play.hasClassName("on"))
        {
            play.addClassName("on");
            sound.play();
        } 
        
        var click = event.layerX;
        if (click == "undefined")
            click = event.offsetX;
        
        var time = (click * sound.durationEstimate) / progressContainer.getWidth();
        
        if (time > sound.duration)
            time = sound.duration * 0.95;
        
        sound.setPosition(time);
        event.stop();
    });

    loop.observe('click', function (event)
    {
        if (loop.hasClassName("on"))
            loop.removeClassName("on");
        else
            loop.addClassName("on");

        event.stop();
    });
    
    play.observe('click', function (event)
    {
        if (play.hasClassName("on"))
        {
            play.removeClassName("on");
            progress.style.width = 0;
            sound.stop();
            updateTimeDisplay(0);
        }
        else
        {
            play.addClassName("on");
            sound.play();
        }
        event.stop();
    });
}
