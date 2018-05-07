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
            var map = new mapboxgl.Map({
              container: 'map_canvas', // HTML container id
              style: 'mapbox://styles/mapbox/satellite-v9', // style URL
              center: [24, 22], // starting position as [lng, lat]
              zoom: 1
            });
            map.addControl(new mapboxgl.NavigationControl());

            // Add markers for each sound
            var geojson_features = [];
            var bounds = new mapboxgl.LngLatBounds();

            $.each(data, function(index, item) {
                var id = item[0];
                var lat = item[1];
                var lon = item[2];

                geojson_features.push({
                    "type": "Feature",
                    "properties": {
                        "id": id,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [ lon, lat ]
                    }
                });
                bounds.extend([lon, lat]);
            });

            map.on('load', function() {
                map.loadImage('/media/images/map_icon.png', function(error, image) {

                    if (error) throw error;
                    map.addImage("custom-marker", image);


                    // Add a new source from our GeoJSON data and set the
                    // 'cluster' option to true. GL-JS will add the point_count property to your source data.
                    map.addSource("sounds", {
                        type: "geojson",
                        data: {
                            "type": "FeatureCollection",
                            "features": geojson_features
                        },
                        cluster: true,
                        clusterMaxZoom: 10, // Max zoom to cluster points on
                        clusterRadius: 50 // Radius of each cluster when clustering points (defaults to 50)
                    });

                    map.addLayer({
                        id: "sounds-clusters",
                        type: "circle",
                        source: "sounds",
                        filter: ["has", "point_count"],
                        paint: {
                            // Use step expressions (https://www.mapbox.com/mapbox-gl-js/style-spec/#expressions-step)
                            // with three steps to implement three types of circles:
                            //   * Blue, 20px circles when point count is less than 100
                            //   * Yellow, 30px circles when point count is between 100 and 750
                            //   * Pink, 40px circles when point count is greater than or equal to 750
                            "circle-color": [
                                "step",
                                ["get", "point_count"],
                                "#51bbd6",
                                100,
                                "#f1f075",
                                750,
                                "#f28cb1"
                            ],
                            "circle-radius": [
                                "step",
                                ["get", "point_count"],
                                20,
                                100,
                                30,
                                750,
                                40
                            ]
                        }
                    });

                    map.addLayer({
                        id: "sounds-cluster-labels",
                        type: "symbol",
                        source: "sounds",
                        filter: ["has", "point_count"],
                        layout: {
                            "text-field": "{point_count_abbreviated}",
                            "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
                            "text-size": 12
                        }
                    });

                    map.addLayer({
                        id: "sounds-unclustered",
                        type: "symbol",
                        source: "sounds",
                        filter: ["!has", "point_count"],
                        layout: {
                            "icon-image": "custom-marker"
                        }
                    });

                    // popups
                    map.on('click', 'sounds-unclustered', function (e) {

                        stopAll();
                        var coordinates = e.features[0].geometry.coordinates.slice();
                        var sound_id = e.features[0].properties.id;

                        ajaxLoad( '/geotags/infowindow/' + sound_id, function(data, responseCode)
                        {

                            // Ensure that if the map is zoomed out such that multiple
                            // copies of the feature are visible, the popup appears
                            // over the copy being pointed to.
                            while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
                                coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
                            }

                            var popup = new mapboxgl.Popup()
                                .setLngLat(coordinates)
                                .setHTML(data.response)
                                .addTo(map);

                            popup.on('close', function(e) {
                                stopAll();  // Stop sound on popup close
                            });

                            makePlayer('.infowindow_player .player');

                        });

                    });

                    // Change the cursor to a pointer when the mouse is over the places layer.
                    map.on('mouseenter', 'sounds-unclustered', function () {
                        map.getCanvas().style.cursor = 'pointer';
                    });

                    // Change it back to a pointer when it leaves.
                    map.on('mouseleave', 'sounds-unclustered', function () {
                        map.getCanvas().style.cursor = '';
                    });

                    // Other stuff
                    // Set map boundaries
                    if ((center_lat !== undefined) && (center_lon !== undefined) && (zoom !== undefined)){
                        // If these parameters are specified, do center using them
                        //map.setCenter(new google.maps.LatLng(center_lat, center_lon));
                        //map.setZoom(zoom);
                    } else {
                        if (nSounds > 1){
                            map.fitBounds(bounds);
                        } else {
                            //map.setCenter(lastPoint, 4); // Center the map in the geotag
                        }
                    }

                    // Run callback function (if passed) after map is built
                    if (on_built_callback !== undefined){
                        on_built_callback();
                    }

                    // Add listener for callback on bounds changed
                    /*
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
                    });*/


                });
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
