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

// set up the rating stars to use ajax
function setupStarRatings()
{
    $("ul.star-rating > li > a").click(function (event) {
        event.preventDefault();

        if (!isLoggedIn)
        {
            this.href = loginUrl;
            return;
        }
        
        $.get(
            this.href,
            function (data)
            {
                var numRatingsElement = $("div.stars > span.numratings");
                if (numRatingsElement.length)
                    numRatingsElement.html("(" + data + ")");
            }
        );
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