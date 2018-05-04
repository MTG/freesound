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

function make_map(geotags_url, map_element_id, extend_initial_bounds, show_clusters, on_built_callback, on_bounds_changed_callback, center_lat, center_lon, zoom){
    /*
    This function is used to display maps in the user home/profile and in the pack page.
    'geotags_url' is a Freesound URL that returns the list of geotags that will be shown in the map.
    'element_id' is the DOM element where the map will be shown.
    Google Maps API is only called if 'geotags_url' returns at least one geotag.
    TODO: update docs of this function
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
            var markers = [];  // only used for clustering

            $.each(data, function(index, item) {
                var id = item[0];
                var lat = item[1];
                var lon = item[2];

                var point = new google.maps.LatLng(lat, lon);
                lastPoint = point;
                if (extend_initial_bounds){
                    bounds.extend(point);
                }

                var marker = new google.maps.Marker({'position': point, 'map': map});
                if (show_clusters) {
                    markers.push(marker);
                }

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

            // Show map element id (if provided)
            if (map_element_id !== undefined){
                $(map_element_id).show();
            }

            // Set map boundaries
            if ((center_lat !== undefined) && (center_lon !== undefined) && (zoom !== undefined)){
                // If these parameters are specified, do center using them
                map.setCenter(new google.maps.LatLng(center_lat, center_lon));
                map.setZoom(zoom);
            } else {
                google.maps.event.trigger(map, 'resize');
                if (nSounds > 1){
                    if (!bounds.isEmpty()) map.fitBounds(bounds);
                } else {
                    map.setCenter(lastPoint, 4); // Center the map in the geotag
                }
            }

            // Cluster map points
            if (show_clusters) {
                var mcOptions = { gridSize: 50, maxZoom: 12, imagePath:'/media/images/js-marker-clusterer/m' };
                new MarkerClusterer(map, markers, mcOptions);
            }

            // Run callback function (if passed) after map is built
            if (on_built_callback !== undefined){
                on_built_callback();
            }

            // Add listener for callback on bounds changed
            if (on_bounds_changed_callback !== undefined){
                google.maps.event.addListener( map, 'bounds_changed', function() {
                    var bounds = map.getBounds();
                    on_bounds_changed_callback(  // The callback is called with the following arguments:
                        map.getCenter().lat(),  // Latitude (at map center)
                        map.getCenter().lng(),  // Longitude (at map center)
                        map.getZoom(),  // Zoom
                        bounds.getSouthWest().lat(),  // Latidude (at bottom left of map)
                        bounds.getSouthWest().lng(),  // Longitude (at bottom left of map)
                        bounds.getNorthEast().lat(),  // Latidude (at top right of map)
                        bounds.getNorthEast().lng()   // Longitude (at top right  of map)
                    )
                });
            }
        }
    });
}
