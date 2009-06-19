google.load("prototype", "1.6.0.3");
google.load("swfobject", "2.2")
google.setOnLoadCallback(function() {
    setupStarRatings();
    switchFormSubmits()
});

// set up the rating stars to use ajax
function setupStarRatings()
{
    $$("ul.star-rating > li > a").each(function (element) {
        element.observe("click", function (event) {
            if (!isLoggedIn)
            {
                element.href = loginUrl;
                return;
            }

            new Ajax.Request(element.href, {
                method: 'get',
                onSuccess: function(transport) {
                    var numRatingsElement = $$("div.stars > span.numratings").first();
                    if (numRatingsElement)
                        numRatingsElement.update("(" + transport.responseText + ")");
                }
            });
            
            event.stop();
        });
    });
}

function switchFormSubmits()
{
    if (!isLoggedIn)
    {
        $('sound_comment_submit').value = "Please log in to comment";
        $('sound_comment_submit').disable();
    }
}

// ----------GOOGLE MAPS FUNCTION -------------
function zoomToBounds(map, bounds)
{
    var center = bounds.getCenter();
    var newZoom = map.getBoundsZoomLevel(bounds) - 1;
    if (map.getZoom() != newZoom)
    {
        map.setCenter(center, newZoom);
    }
    else
    {
        map.panTo(center);
    }
}