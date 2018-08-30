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
});

function remove_explicit_content_warning(element){
    var warning = $(element).parent().parent('.explicit_content_text');
    var player = $(element).parent().parent().parent();
    player.find('.sample_player').removeClass('blur');
    player.find('.sample_information').removeClass('blur');
    warning.remove();
}

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

    $(".disable-on-submit").submit(function () {
       $(this).find('input[type="submit"]').attr("disabled", true);
       return true;
    });
});

var voted = {};

// set up the rating stars to use ajax
function setupStarRatings()
{
    $("ul.star-rating > li > a").click(function (event) {
        event.preventDefault();

        // take the sound id from the voting url
        var splitted_href = this.href.split('/');
        var vote_key = splitted_href[splitted_href.length-4];
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

// FOOTER BANNER
function hideFooterBanner(){
    $('#footerBanner').hide(200);
}

function showFooterBanner() {
    $('#footerBanner').show(200);
}

// Modals
function hideModal(){
    $("#fsmodal").hide();
}

function openModal(){
    $("#fsmodal").show();
    $("#fsmodal").find('.close-modal').click(hideModal);
}

function afterDownloadModal(show_modal_url, sound_name){
    hideModal(); // Hide the modal just in case it was shown
    // Send request to server which will decide whether to show or not the modal and return the contents
    $.getJSON(show_modal_url, {sound_name:sound_name},
        function(resp) {
            if (resp.content){
                // If JSON response has content, then the modal should be shown
                $('#fsmodal').html(resp.content);
                openModal();
            }
        });
}
function unsecureImageCheck(input) {
    var div = $("<div>", {class: "unsecure_image_warning"});
    div.append("<b>Warning</b>: We only support images from HTTPS locations. Images from an HTTP location will appear as a link.");
    div.insertBefore(input);
    div.hide();

    function show_message_if_insecure(){
        var txt = input.val();
        var regular_expression = new RegExp('.*<img.+src=.?http:.*', 'i');
        var is_unsecure = regular_expression.test(txt);
        div.toggle(is_unsecure);
    }
      
    // When the user enters text we check if it contains unsecure uri
    input.bind('keydown focusin', function(){
        setTimeout(function(){
            // We need the timeout for the paste event to make sure the text has been pasted when evaluated
            show_message_if_insecure();
        }, 100);
    });
}


// Util funtion to update query params in a URL string
function updateQueryStringParameter(uri, key, value) {
    var re = new RegExp("([?&])" + key + "=.*?(&|#|$)", "i");
    if (uri.match(re)) {
        return uri.replace(re, '$1' + key + "=" + value + '$2');
    } else {
        var hash =  '';
        if( uri.indexOf('#') !== -1 ){
            hash = uri.replace(/.*#/, '#');
            uri = uri.replace(/#.*/, '');
        }
        var separator = uri.indexOf('?') !== -1 ? "&" : "?";
        return uri + separator + key + "=" + value + hash;
    }
}
