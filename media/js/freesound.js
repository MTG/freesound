/*
 *
 * Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
 *
 * Freesound is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * Freesound is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *   See AUTHORS file.
 */

$(function() {
    cookieValue = $.cookie("cookieConsent");
    if (cookieValue == "yes")
        $("#cookie-bar").remove();

    $("#cookie-accept").click(function() {
        $.cookie("cookieConsent", "yes", { expires: 360, path: '/' });
        $("#cookie-bar").fadeOut(500);
    });

    $(".tag_group").hover(
        function() {
            $(this).css("background", "rgb(230,230,230)");
            $(this).find("a").css("background-image", "url(/media/images/tag_edge_group_hover.png)");
        },
        function() {
            $(this).css("background", "rgb(244,244,244)");
            $(this).find("a").css("background-image", "url(/media/images/tag_edge_group.png)");
        }
    );
    
    $(".explicit_content_text span a").click(function(e) {
        var warning = $(this).parent().parent('.explicit_content_text');
        var sample_player_small = $(this).parent().parent().parent();
        sample_player_small.find('.sample_player').removeClass('blur');
        sample_player_small.find('.sample_information').removeClass('blur');
        warning.remove();
        e.preventDefault()
    })

});

function d()
{
    if (window.console && window.console.log)
    {
        $.each(arguments, function (index, element) { console.log(element) });
    }
    else
    {
        alert("trying to debug but there is no console");
    }
}

$(document).ready( function() {
    setupStarRatings();
    switchFormSubmits();
});

var voted = {};

// set up the rating stars to use ajax
function setupStarRatings()
{
    $("ul.star-rating > li > a").click(function (event) {
        event.preventDefault();

        // take the sound id from the voting url
        var splitted_href = this.href.split('/');
        var vote_key = splitted_href[splitted_href.length-3];
        if(!voted[vote_key]) {
            if (!isLoggedIn)
            {
                this.href = loginUrl;
                return;
            }
            this.style.zIndex = 11;
            this.style.background = 'url(/media/images/stars.gif) left bottom repeat-x';
            voted[vote_key] = true;

            $.get(
                this.href,
                function (data)
                {
                    var numRatingsElement = $("div.stars > span.numratings");
                    if (numRatingsElement.length)
                        numRatingsElement.html("(" + data + ")");
                }

            );
        }
    });
}

function switchFormSubmits()
{
    if (!isLoggedIn)
    {
        if ($('#sound_comment_submit').length)
        {
            $('#sound_comment_submit').attr('disabled', 'disabled');
            $('#sound_comment_submit').val("Please log in to comment");
        }
    }
}


// BOOKMARKS related

function show_hide_bookmark_form(id)
{
    if( $("#bookmark_form_"  + id.toString()).is(':hidden') ) { // Only do the request when expanding the div
        var url = location.protocol + '//' + location.hostname + (location.port ? ':'+ location.port: '') + "/home/bookmarks/get_form_for_sound/" + id.toString() + '/';
        $("#bookmark_form_"  + id.toString()).html('&nbsp;').load(url)
    }
    $("#bookmark_form_"  + id.toString()).toggle();
}
