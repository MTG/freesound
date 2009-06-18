google.load("prototype", "1.6.0.3");
google.load("swfobject", "2.2")
google.setOnLoadCallback(function() {
    setupStarRatings();
});

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