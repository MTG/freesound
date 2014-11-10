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
