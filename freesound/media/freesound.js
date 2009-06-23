google.load("prototype", "1.6.0.3");
google.load("swfobject", "2.2")

google.setOnLoadCallback(function() {
    setupStarRatings();
    switchFormSubmits();
    setupFaceting();
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
        if ($('sound_comment_submit'))
        {
            $('sound_comment_submit').value = "Please log in to comment";
            $('sound_comment_submit').disable();
        }
    }
}

function setupFaceting()
{
    $$(".facet_item").each(function (element) {
        element.observe("mouseover", function (event) {
            element.down("span.facet_addremove").show()
        })
        element.observe("mouseout", function (event) {
            element.down("span.facet_addremove").hide()
        })
    });
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