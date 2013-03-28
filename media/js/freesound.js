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

function auto_suggest(tb_id,url){
		        $(tb_id).autocomplete(url, {
		            dataType: 'json',
		            width: 500,  
		            max: 50,
		            parse: function(data) {
		                return $.map(data, function(row) {
							return { data:row, value:row[0], result:row[1] };
		                });
		            }
		            }).result(
		                function(e, data, value) {
		                    $(tb_id).val(data[0]);
		                }
		            );
}

// ----------GOOGLE MAPS FUNCTION -------------
function zoomToBounds(map, bounds)
{
    var center = bounds.getCenter();
    var newZoom = map.getBoundsZoomLevel(bounds) - 1;

    if (newZoom < 0)
        newZoom = 0;

    if (map.getZoom() != newZoom)
    {
        map.setCenter(center, newZoom);
    }
    else
    {
        map.panTo(center);
    }
}

function setMaxZoomCenter(map, lat, lng, zoom)
{
    var latlng = new GLatLng(lat, lng);

    map.getCurrentMapType().getMaxZoomAtLatLng(latlng, function(response)
    {
        if (response && response['status'] == G_GEO_SUCCESS)
        {
            map.setCenter(latlng, response['zoom']);
        }
        else
        {
            map.setCenter(latlng, zoom);
        }
    });
}