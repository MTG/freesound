function setMaxZoomCenter(lat, lng, zoom) {
    /*  Center a map to a given latitude, longitude and zoom.  */
    var latlng = new google.maps.LatLng(lat, lng);
    window.map.setCenter(latlng);
    window.map.setZoom(zoom);
}

function getSoundsLocations(url, callback){
    /*
    Loads geotag data from Freesound endpoint and returns as list of tuples with:
      [(sound_id, sound_latitude, sound_longitude), ...]
     */
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

function make_sounds_map(geotags_url, map_element_id, on_built_callback, on_bounds_changed_callback,
                         center_lat, center_lon, zoom){
    /*
    This function is used to display maps with sounds. It is used in all pages where maps with markers (which represent
    sounds) are shown: user home/profile, pack page, geotags map, embeds. Parameters:

    - geotags_url: Freesound URL that returns the list of geotags that will be shown in the map.
    - map_element_id: DOM element id where the map will be placed.
    - on_built_callback: function to be called once the map has been built (takes no parameters)
    - on_bounds_changed_callback: function called when the bounds of the map change (because of user interaction). As
        parameters it gets the map ID, updated center latitude, center longitude and zoom, as well as bottom left
        corner latitude and longitude, and top right corner latitude and longitude (see code below for more
        specific details).
    - center_lat: latitude where to center the map (if not specified, it is automatically determined based on markers)
    - center_lon: latitude where to center the map (if not specified, it is automatically determined based on markers)
    - zoom: initial zoom for the map (if not specified, it is automatically determined based on markers)

    This function first calls the Freesound endpoint which returns the list of geotags to be displayed as markers.
    Once the data is received, it creates the map and does all necessary stuff to display it.

    NOTE: the map created using this function is assigned to window.map to make it accessible from everywhere. This is
    needed for the "zoom in" method in info windows. If more than one map is shown in a single page (which does not
    happen in Freesound) the "zoom in" method in inforwindows won't work properly.
     */

    getSoundsLocations(geotags_url, function(data){
        var nSounds = data.length;
        if (nSounds > 0) {  // only if the user has sounds, we render a map

            // Init map and info window objects
            var map = new google.maps.Map(
                document.getElementById(map_element_id), {
                center: new google.maps.LatLng(24, 22),
                zoom: 2, minZoom: 2,
                mapTypeId: google.maps.MapTypeId.SATELLITE,
                scrollwheel: false,
                streetViewControl: false
                });
            window.map = map;  // Make map a property of window, accessible from anywhere

            var infowindow = new google.maps.InfoWindow();
            google.maps.event.addListener(infowindow, 'closeclick', function() {
                stopAll();
            });

            // Add markers for each sound
            var markers_bounds = new google.maps.LatLngBounds();
            var lastPoint;
            var markers = [];  // only used for clustering

            $.each(data, function(index, item) {
                var id = item[0];
                var lat = item[1];
                var lon = item[2];

                var point = new google.maps.LatLng(lat, lon);
                lastPoint = point;
                markers_bounds.extend(point);

                var marker = new google.maps.Marker({'position': point, 'map': map});
                markers.push(marker);

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

            // Set map boundaries
            if ((center_lat !== undefined) && (center_lon !== undefined) && (zoom !== undefined)){
                // If these parameters are specified, do center using them
                map.setCenter(new google.maps.LatLng(center_lat, center_lon));
                map.setZoom(Math.round(parseFloat(zoom)));
            } else {
                google.maps.event.trigger(map, 'resize');
                if (nSounds > 1){
                    map.fitBounds(markers_bounds);
                } else {
                    map.setCenter(lastPoint, 4); // Center the map in the geotag
                }
            }

            // Cluster map points
            var mcOptions = { gridSize: 50, maxZoom: 12, imagePath:'/media/images/js-marker-clusterer/m' };
            new MarkerClusterer(map, markers, mcOptions);

            // Run callback function (if passed) after map is built
            if (on_built_callback !== undefined){
                on_built_callback();
            }

            // Add listener for callback on bounds changed
            google.maps.event.addListener( map, 'bounds_changed', function() {
                if (on_bounds_changed_callback !== undefined) {
                    var bounds = map.getBounds();
                    on_bounds_changed_callback(  // The callback is called with the following arguments:
                        map_element_id, // ID of the element containing the map
                        map.getCenter().lat(),  // Latitude (at map center)
                        map.getCenter().lng(),  // Longitude (at map center)
                        map.getZoom(),  // Zoom
                        bounds.getSouthWest().lat(),  // Latidude (at bottom left of map)
                        bounds.getSouthWest().lng(),  // Longitude (at bottom left of map)
                        bounds.getNorthEast().lat(),  // Latidude (at top right of map)
                        bounds.getNorthEast().lng()   // Longitude (at top right  of map)
                    )
                }
            });
        }
    });
}


function make_geotag_edit_map(map_element_id, arrow_url, on_bounds_changed_callback,
                              center_lat, center_lon, zoom){

    /*
    This function is used to display the map used to add a geotag to a sound maps with sounds. It is used in the sound
    edit page and the sound describe page.

    - map_element_id: DOM element id where the map will be placed.
    - on_bounds_changed_callback: function called when the bounds of the map change (because of user interaction). As
        parameters it gets the map ID, updated center latitude, center longitude and zoom, as well as bottom left
        corner latitude and longitude, and top right corner latitude and longitude (see code below for more
        specific details).
    - center_lat: latitude where to center the map (if not specified, it uses a default one)
    - center_lon: latitude where to center the map (if not specified, it uses a default one)
    - zoom: initial zoom for the map (if not specified, it uses a default one)

    This function returns the object of the map that has been created.
     */

    // Initialize map
    if (center_lat === undefined){  // Load default center
        center_lat = 23.8858;
        center_lon = 21.7968;
        zoom = 2;
    }

    var initial_center = new google.maps.LatLng(parseFloat(center_lat, 10), parseFloat(center_lon, 10));
    var map = new google.maps.Map(
        document.getElementById(map_element_id), {
          center: initial_center,
          zoom: parseInt(zoom, 10),
          mapTypeId: google.maps.MapTypeId.SATELLITE,
          scrollwheel: false,
          streetViewControl: false,
    });

    // Add arrow marker
    var image = {
        url: arrow_url,
        size: new google.maps.Size(25, 24),
        anchor: new google.maps.Point(0, 24)
    };
    var centerMarker = new google.maps.Marker({
          position: initial_center,
          map: map,
          icon: image
    });

    // Add listener for callback on bounds changed
    google.maps.event.addListener(map, 'bounds_changed', function() {
        if (on_bounds_changed_callback !== undefined) {
            var bounds = map.getBounds();
            on_bounds_changed_callback(  // The callback is called with the following arguments:
                map_element_id, // ID of the element containing the map
                map.getCenter().lat(),  // Latitude (at map center)
                map.getCenter().lng(),  // Longitude (at map center)
                map.getZoom(),  // Zoom
                bounds.getSouthWest().lat(),  // Latidude (at bottom left of map)
                bounds.getSouthWest().lng(),  // Longitude (at bottom left of map)
                bounds.getNorthEast().lat(),  // Latidude (at top right of map)
                bounds.getNorthEast().lng()   // Longitude (at top right  of map)
            );
        }
        centerMarker.setPosition(map.getCenter());  // Update arrow marker
    });

    return map;
}
