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

function getSoundsLocations(url, callback){
    var resp = [];
    var oReq = new XMLHttpRequest();
    oReq.open("GET", url, true);
    oReq.responseType = "arraybuffer";
    oReq.onload = function(oEvent) {
        var raw_data = new Int32Array(oReq.response);

        var id = null;
        var lat = null;
        var lon = null;

        for (var i = 0; i < raw_data.length; i += 3) {
            id = raw_data[i];
            lat = raw_data[i+1] / 1000000;
            lon = raw_data[i+2] / 1000000;
            resp.push([id, lat, lon]);
        }
        callback(resp);
    };
    oReq.send();
}

function make_map(geotags_url, element_id){
    /*
    This function is used to display maps in the user home/profile and in the pack page.
    'geotags_url' is a Freesound URL that returns the list of geotags that will be shown in the map.
    'element_id' is the DOM element where the map will be shown.
    Google Maps API is only called if 'geotags_url' returns at least one geotag.
    TODO: generalize this function so that it can be used in all places where maps are shown (geotags page, map embeds...)
     */
    getSoundsLocations(geotags_url, function(data){
        var nSounds = data.length;
        if (nSounds > 0) {  // only if the user has sounds, we render a map

            // Init map and info window objects
            var map = new google.maps.Map(
                document.getElementById('map_canvas'), {
                center: new google.maps.LatLng(24, 22),
                zoom: 2,
                mapTypeId: google.maps.MapTypeId.SATELLITE,
                scrollwheel: false,
                streetViewControl: false
                });
            var infowindow = new google.maps.InfoWindow();
            google.maps.event.addListener(infowindow, 'closeclick', function() {
                stopAll();
            });

            // Add markers for each sound
            var bounds = new google.maps.LatLngBounds();
            var lastPoint;
            $.each(data, function(index, item) {
                var id = item[0];
                var lat = item[1];
                var lon = item[2];

                var point = new google.maps.LatLng(lat, lon);
                lastPoint = point;
                bounds.extend(point);
                var marker = new google.maps.Marker({'position': point, 'map': map});

                google.maps.event.addListener(marker, 'click', function()
                {
                    stopAll();
                    ajaxLoad( '/geotags/infowindow/' + id, function(data, responseCode)
                    {
                        infowindow.setContent(data.response);
                        infowindow.open(map, marker);
                        setTimeout(function() {
                            makePlayer('.infowindow_player .player');
                        }, 500);
                    });
                });
            });

            // Show map and set boundaries
            $(element_id).show();
            google.maps.event.trigger(map, 'resize');
            if (nSounds > 1){
                if (!bounds.isEmpty()) map.fitBounds(bounds);
            }else{
                map.setCenter(lastPoint, 4); // Center the map in the geotag
            }
        }
    });
}
