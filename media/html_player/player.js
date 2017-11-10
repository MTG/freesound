soundManager.useHTML5Audio = true;
soundManager.url = '/media/html_player/swf/';
//flash 9 doesn't have weird artifacts at the beginning of sounds.
soundManager.flashVersion = 9;
soundManager.debugMode = false;
//soundManager.preferFlash = true;
// If the player is used in an embed, it uses HTML5 so it is lighter (althogh playbar position is not updated as fast as with flash)
//if (typeof isEmbed!="undefined"){
//    soundManager.preferFlash = false;
//}
//if you have a stricter test than 'maybe' SM will switch back to flash.
//soundManager.html5Test = /^maybe$/i

$(function()
{
	$.extend($.fn.disableTextSelect = function()
	{
		return this.each(function()
		{
			if($.browser.mozilla)
			{   //Firefox
				$(this).css('MozUserSelect','none');
			}
			else if($.browser.msie)
			{
			    //IE
				$(this).bind('selectstart',function(){return false;});
			}
			else
			{
			    //Opera, etc.
				$(this).mousedown(function(){return false;});
			}
		});
	});
	$('.noSelect').disableTextSelect();//No text selection on elements with a class of 'noSelect'
});

function msToTime(position, durationEstimate, displayRemainingTime, showMs)
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

    if (showMs)
        return (displayRemainingTime ? "-" : " ") + minutes + ':' + seconds + ':' + ms;
    else
        return (displayRemainingTime ? "-" : " ") + minutes + ':' + seconds;
}

var uniqueId = 0;
var _mapping = [];
var y_min = Math.log(100.0) / Math.LN10;
var y_max = Math.log(22050.0) / Math.LN10;

for (var y = 200;y >= 0; y--)
    _mapping.push(Math.pow(10.0, y_min + y / 200.0 * (y_max - y_min)));

function switchToggle(element)
{
    if (element.hasClass("toggle"))
    {
        element.removeClass("toggle");
        element.addClass("toggle-alt");
    }
    else if (element.hasClass("toggle-alt"))
    {
        element.removeClass("toggle-alt");
        element.addClass("toggle");
    }
    element.toggleClass("on");
}


function switchOff(element)
{
    element.addClass("toggle");
    element.removeClass("toggle-alt");
    element.removeClass("on");
}


function switchOn(element)
{
    element.removeClass("toggle");
    element.addClass("toggle-alt");
    element.addClass("on");
}


function getPlayerPosition(element)
{
    el = element[0];
    for (var lx=0, ly=0;
         el != null;
         lx += el.offsetLeft, ly += el.offsetTop, el = el.offsetParent);
    return [lx, ly];
}


function stopAll(exclude)
{
    var ids = soundManager.soundIDs;
    ids = jQuery.grep(ids, function(value)
    {
        if(exclude)
            return value != exclude.sID;
        else
            return true;
    });
    switchOff($(".player .play"));
    for(var i=0; i<ids.length; i++)
    {
        soundManager.pause(ids[i]);
    }
}


function getMousePosition(event, playerElement)
{
    var posx = 0;
    var posy = 0;
    if (!event) var event = window.event;
    if (event.pageX || event.pageY)
    {
        posx = event.pageX;
        posy = event.pageY;
    }
    else if (event.clientX || event.clientY)
    {
        posx = event.clientX + document.body.scrollLeft + document.documentElement.scrollLeft;
        posx = event.clientY + document.body.scrollTop + document.documentElement.scrollTop;
    }
    ppos = getPlayerPosition(playerElement);
    return [posx-ppos[0], posy-ppos[1]];
}


function makePlayer(selector) {
    $(selector).each( function () {

        if ($(this).data("hasPlayer")) return true;
        else $(this).data("hasPlayer", true);

        var showMs = $(this).hasClass("large");

        if ($(this).hasClass("large"))
        {
            $(this).append('<div class="controls"> \
                   <a href="javascript:void(0)" title="play / pause" class="toggle play">play / pause</a> \
                   <a href="javascript:void(0)" title="stop" class="button stop">stop</a> \
                   <a href="javascript:void(0)" title="change display" class="toggle display">change display</a> \
                   <a href="javascript:void(0)" title="loop" class="toggle loop">loop</a> \
                   <a href="javascript:void(0)" title="toggle measure" class="toggle measure">toggle measure</a> \
                </div> \
                <div class="background"></div> \
                <div class="measure-readout-container"><div class="measure-readout"></div></div> \
                <div class="loading-progress"></div> \
                <div class="position-indicator"></div> \
                <div class="time-indicator-container"><div class="time-indicator"></div></div>');
        }
        else if ($(this).hasClass("small"))
        {
            $(this).append('<div class="controls"> \
                    <a href="javascript:void(0)" title="play / pause" class="toggle play">play / pause</a> \
                    <a href="javascript:void(0)" title="loop" class="toggle loop">loop</a> \
                </div> \
                <div class="background"></div> \
                <div class="loading-progress"></div> \
                <div class="position-indicator"></div> \
                <div class="time-indicator-container"><div class="time-indicator"></div></div>');

            // Check if toggle display button should be added and add it if requested
            if (typeof showToggleDisplayButton !== "undefined"){
                if (showToggleDisplayButton){
                    var toggle_display_button = '<a href="javascript:void(0)" title="change display" class="toggle display">change display</a>';
                    var cotrols_element = $('.controls');
                    cotrols_element.css('width', '60px');
                    cotrols_element.append(toggle_display_button);
                }
            }
        }
        else if ($(this).hasClass("mini")) {
            $(this).append('<div class="controls"> \
                   <a href="javascript:void(0)" title="play / pause" class="toggle play">play / pause</a> \
                   <a href="javascript:void(0)" title="loop" class="toggle loop"></a> \
                </div> \
                <div class="background"></div> \
                <div class="loading-progress"></div> \
                <div class="position-indicator"></div>');
        }
        
        $("*", this).disableTextSelect();

        var mp3Preview = $(".metadata .mp3_file", this).attr('href');
        var oggPreview = $(".metadata .ogg_file", this).attr('href');
        var waveform = $(".metadata .waveform", this).attr('href');
        var spectrum = $(".metadata .spectrum", this).attr('href');
        var duration = $(".metadata .duration", this).text();

        var playerElement = $(this);

        if (!$(this).hasClass("mini"))
            $(".background", this).css("backgroundImage", 'url("' + waveform + '")');
            $(".background", this).css("backgroundSize", 'contain');
            $(".background", this).css("backgroundRepeat", 'no-repeat');

        $(".loading-progress", playerElement).hide();

        $(".time-indicator", playerElement).html(msToTime(0, duration, !$(".time-indicator-container", playerElement).hasClass("on"), showMs));

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
                var loaded = this.bytesLoaded / this.bytesTotal * 100;
                if(loaded > 0) $(".loading-progress", playerElement).show();
                $(".loading-progress", playerElement).css("width", (100 - loaded) + "%");
                $(".loading-progress", playerElement).css("left", loaded + "%");
            },
            whileplaying: function()
            {
                var positionPercent = this.position / duration * 100;
                $(".position-indicator", playerElement).css("left", positionPercent + "%");
                $(".time-indicator", playerElement).html(msToTime(sound.position, duration, !$(".time-indicator-container", playerElement).hasClass("on"), showMs));
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
        });

        $(".play", this).bind("toggle", function (event, on)
        {
            if (on)
            {
                switchOn($(".play", playerElement));
                sound.play();
            }
            else
            {
                switchOff($(".play", playerElement));
                sound.pause();
            }
        });

        $(".stop", this).click(function (event)
        {
            event.stopPropagation();
            if (sound.playState == 1 || !sound.paused)
            {
                sound.stop();
                sound.setPosition(0);
                $(".time-indicator", playerElement).html(
                        msToTime(sound.position,
                                sound.duration,
                                !$(".time-indicator-container", playerElement).hasClass("on"),
                                showMs));
                $(".position-indicator", playerElement).css("left", "0%");
                switchOff($(".play", playerElement));
            }
        });

        $(".display", this).bind("toggle", function (event, on)
        {
            if (on)
                $(".background", playerElement).css("background", "url(" + spectrum + ")");
            else
                $(".background", playerElement).css("background", "url(" + waveform + ")");
            $(".background", playerElement).css("backgroundSize", 'contain');
            $(".background", playerElement).css("backgroundRepeat", 'no-repeat');
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
            var pos = getMousePosition(event, $(this));
            sound.setPosition(duration * pos[0] / $(this).width());
            if (sound.playState == 0 || sound.paused)
            {
                sound.play();
                switchOn($(".play", playerElement));
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
        },function()
        {
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
            pos = getMousePosition(event, $(this));

            if ($(".display", playerElement).hasClass("on"))
            {
                readout = _mapping[Math.floor(pos[1])].toFixed(2) + "hz";
            }
            else
            {
                var height2 = $(this).height()/2;

                if (pos[1] == height2)
                    readout = "-inf";
                else
                    readout = (20 * Math.log( Math.abs(pos[1]/height2 - 1) ) / Math.LN10).toFixed(2);

                readout = readout + " dB";
            }

            $('.measure-readout', playerElement).html(readout);
        });

        // Check if spectrogram image should be used by default
        if (!$(this).hasClass("mini")) {
            if (typeof spectrogramByDefault !== "undefined") {
                if (spectrogramByDefault) {
                    var display_element = $('.display');
                    if (display_element.length !== 0) {
                        // Switch to to background spectrogram by simulating click on toggle button
                        display_element.trigger('click');
                    } else {
                        // Switch to to background spectrogram by replacing the image (toggle display button does not exist)
                        $(".background", playerElement).css("background", "url(" + spectrum + ")");
                        $(".background", playerElement).css("backgroundSize", 'contain');
                        $(".background", playerElement).css("backgroundRepeat", 'no-repeat');
                    }
                }
            }
        }

        return true;
    });
}


$(function() {
    $(".toggle, .toggle-alt").live("click", function (event)
    {
        event.stopPropagation();
        switchToggle($(this));
        $(this).trigger("toggle", $(this).hasClass("on"));
    });

    soundManager.onready(function()
    {
        makePlayer('.player');
    });
});
