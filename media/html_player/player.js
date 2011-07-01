soundManager.url = '/media/html_player/swf/';
soundManager.flashVersion = 8; // optional: shiny features (default = 8)
soundManager.useFlashBlock = false; // optionally, enable when you're ready to dive in
soundManager.debugMode = false;

function msToTime(position, durationEstimate, displayRemainingTime)
{
    if (displayRemainingTime)
        position = durationEstimate - position;

    var ms = parseInt(position % 1000);
    if (ms < 10)
        ms = '00' + ms
    else if (ms < 100)
        ms = '0' + ms;
    else
        ms = '' + ms;

    var s = parseInt(position / 1000);
    var seconds = parseInt(s % 60);
    var minutes = parseInt(s / 60);
    if (seconds < 10)
        seconds = '0' + seconds;
    else
        seconds = '' + seconds;

    if (minutes < 10)
        minutes = '0' + minutes;
    else
        minutes = '' + minutes;

    return (displayRemainingTime ? "-" : " ") + minutes + ':' + seconds + ':' + ms;
}

var uniqueId = 0;

var _mapping = [];

var y_min = Math.log(100.0) / Math.LN10;
var y_max = Math.log(22050.0) / Math.LN10;

for (var y = 200;y >= 0; y--)
    _mapping.push(Math.pow(10.0, y_min + y / 200.0 * (y_max - y_min)));


function switchToggle(element) {
    if (element.hasClass("toggle")) {
        element.removeClass("toggle");
        element.addClass("toggle-alt");
    }
    else if (element.hasClass("toggle-alt")) {
        element.removeClass("toggle-alt");
        element.addClass("toggle");
    }
    element.toggleClass("on");
}


function makePlayer(selector) {
    $(selector).each( function () {

        if ($(this).data("hasPlayer")) return true;
        else $(this).data("hasPlayer", true);

        if ($(this).hasClass("large")) {
            $(this).append('<div class="controls"> \
                   <div class="toggle play"></div> \
                   <div class="button stop"></div> \
                   <div class="toggle display"></div> \
                   <div class="toggle loop"></div> \
                   <div class="toggle measure"></div> \
                </div> \
                <div class="background"></div> \
                <div class="measure-readout-container"><div class="measure-readout"></div></div> \
                <div class="loading-progress"></div> \
                <div class="position-indicator"></div> \
                <div class="time-indicator-container"><div class="time-indicator"></div></div>');
        } else if ($(this).hasClass("small")) {
            $(this).append('<div class="controls"> \
                   <div class="toggle play"></div> \
                   <div class="toggle loop"></div> \
                </div> \
                <div class="background"></div> \
                <div class="loading-progress"></div> \
                <div class="position-indicator"></div> \
                <div class="time-indicator-container"><div class="time-indicator"></div></div>');
        } else if ($(this).hasClass("mini")) {
            $(this).append('<div class="controls"> \
                   <div class="toggle play"></div> \
                   <div class="toggle loop"></div> \
                </div> \
                <div class="background"></div> \
                <div class="loading-progress"></div> \
                <div class="position-indicator"></div>');
        }

        var urls = $(".metadata", this).html().split(" ");

        var mp3Preview = urls[0];
        var waveform = urls[1];
        var spectrum = urls[2];
        var duration = urls[3];

        var playerElement = $(this);

        if (!$(this).hasClass("mini"))
            $(".background", this).css("background", "url(" + waveform + ")");

        $(".loading-progress", playerElement).hide();
        $(".time-indicator", playerElement).html(msToTime(0, duration, !$(".time-indicator-container", playerElement).hasClass("on")));

        if ($(this).hasClass("large"))
        {
            $(".controls", this).stop().fadeTo(10000, 0.2);
            $(".measure-readout-container", this).stop().fadeTo(0, 0);
        }

        // Ready to use; soundManager.createSound() etc. can now be called.
        var sound = soundManager.createSound(
        {
            id: "sound-id-" + uniqueId++,
            url: mp3Preview,
            autoLoad: false,
            autoPlay: false,
            onload: function()
            {
                $(".loading-progress", playerElement).remove();
            },
            whileloading: function()
            {
                $(".loading-progress", playerElement).show();

                var loaded = this.bytesLoaded / this.bytesTotal * 100;

                $(".loading-progress", playerElement).css("width", (100 - loaded) + "%");
                $(".loading-progress", playerElement).css("left", loaded + "%");
            },
            whileplaying: function()
            {
                var positionPercent = this.position / this.duration * 100;
                $(".position-indicator", playerElement).css("left", positionPercent + "%");
                $(".time-indicator", playerElement).html(msToTime(sound.position, sound.duration, !$(".time-indicator-container", playerElement).hasClass("on")));
            },
            onfinish: function ()
            {
                if ($(".loop", playerElement).hasClass("on"))
                {
                    sound.play()
                }
                else
                {
                    if ($(".play", playerElement).hasClass("on"))
                        switchToggle($(".play", playerElement));
                }
            }
            //,volume:
        });

        $(".play", this).bind("toggle", function (event, on)
        {
            if (on)
                sound.play()
            else
                sound.pause()
        });

        $(".stop", this).click(function (event)
        {
            event.stopPropagation();
            if (sound.playState)
            {
                sound.stop()
                //sound.setPosition(0);
                $(".time-indicator", playerElement).html(msToTime(sound.position, sound.duration, !$(".time-indicator-container", playerElement).hasClass("on")));
                switchToggle($(".play", playerElement));
            }
        });

        $(".display", this).bind("toggle", function (event, on)
        {
            if (on)
                $(".background", playerElement).css("background", "url(" + spectrum + ")");
            else
                $(".background", playerElement).css("background", "url(" + waveform + ")");
        });

        $(".measure", this).bind("toggle", function (event, on)
        {
            if (on)
                $(".measure-readout-container", playerElement).stop().fadeTo(100, 1.0);
            else
                $(".measure-readout-container", playerElement).stop().fadeTo(100, 0);
        });

        $(".background", this).click(function(event)
        {
            event.stopPropagation();
            sound.setPosition(sound.duration * event.offsetX / $(this).width())
            if (!sound.playState)
            {
                switchToggle($(".play", playerElement));
                sound.play();
            }
        });

        $(".time-indicator-container", this).click(function(event)
        {
            event.stopPropagation();
            $(this).toggleClass("on");
        });

        $(this).hover(function()
        {
            if ($(this).hasClass("large"))
            {
                $(".controls", playerElement).stop().fadeTo(50, 1.0);
                if ($(".measure", playerElement).hasClass("on"))
                    $(".measure-readout-container", playerElement).stop().fadeTo(50, 1.0);
            }
        },function(){
            if ($(this).hasClass("large"))
            {
                $(".controls", playerElement).stop().fadeTo(2000, 0.2);
                if ($(".measure", playerElement).hasClass("on"))
                    $(".measure-readout-container", playerElement).stop().fadeTo(2000, 0.2);
            }
        });

        $(this).mousemove(function (event)
        {
            var readout = "";

            if ($(".display", playerElement).hasClass("on"))
            {
                readout = _mapping[Math.floor(event.offsetY)].toFixed(2) + "hz";
            }
            else
            {
                var height2 = $(this).height()/2;

                if (event.offsetY == height2)
                    readout = "-inf";
                else
                    readout = (20 * Math.log( Math.abs(event.offsetY/height2 - 1) ) / Math.LN10).toFixed(2);

                readout = readout + " dB";
            }

            $('.measure-readout', playerElement).html(readout);
        });
    });
}


$(function() {
    $(".toggle, .toggle-alt").live("click", function (event) {
        event.stopPropagation();
        switchToggle($(this));
        $(this).trigger("toggle", $(this).hasClass("on"));
    });

    // enable HTML5 audio support, if you're feeling adventurous. iPad/iPhone will always get this.
    // soundManager.useHTML5Audio = true;

    soundManager.onready(function() {
        makePlayer('.player');
    });
});
