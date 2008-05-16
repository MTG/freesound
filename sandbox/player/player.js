/*
* player.js -- sound playback using soundManager and only HTML elements
* Copyright (C) 2008 MUSIC TECHNOLOGY GROUP (MTG)
*                    UNIVERSITAT POMPEU FABRA
*
* This program is free software: you can redistribute it and/or modify
* it under the terms of the GNU Affero General Public License as
* published by the Free Software Foundation, either version 3 of the
* License, or (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU Affero General Public License for more details.
*
* You should have received a copy of the GNU Affero General Public License
* along with this program.  If not, see <http://www.gnu.org/licenses/>.
*
* Authors:
*   Bram de Jong <bram.dejong at domain.com where domain in gmail>
*/

soundManager.debugMode = false;
  
soundManager.onload = function() {
    $$('div.preview').each(initPlayer);
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
    // we need to use the "down" method: using childNodes is broken in IE because it -somehow-
    // thinks there are more (or less) text nodes in the code...
    var url = element.down("a.preview-mp3").href;
    var progressContainer = element.down("div.progress-container");
    var position = element.down("div.position");
    var loaded = element.down("div.loaded");
    var rewind = element.down("div.rewind");
    var play = element.down("div.play");
    var loop = element.down("div.loop");
    var timeDisplay = element.down("div.time-display");

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
        }
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
