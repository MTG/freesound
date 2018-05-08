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

function call_on_bounds_chage_callback(map, map_element_id, callback){
    /* Util function used in "make_sounds_map" and "make_geotag_edit_map" to get parameters to cll callback */
    callback(  // The callback is called with the following arguments:
        map_element_id, // ID of the element containing the map
        map.getCenter().lat,  // Latitude (at map center)
        map.getCenter().lng,  // Longitude (at map center)
        map.getZoom(),  // Zoom
        map.getBounds().getSouthWest().lat,  // Latidude (at bottom left of map)
        map.getBounds().getSouthWest().lng,  // Longitude (at bottom left of map)
        map.getBounds().getNorthEast().lat,  // Latidude (at top right of map)
        map.getBounds().getNorthEast().lng   // Longitude (at top right  of map)
    )
}

function make_sounds_map(geotags_url, map_element_id, on_built_callback, on_bounds_changed_callback,
                         center_lat, center_lon, zoom, show_search){
    /*
    This function is used to display maps with sounds. It is used in all pages where maps with markers (which represent
    sounds) are shown: user home/profile, pack page, geotags map, embeds. Parameters:

    - geotags_url: Freesound URL that returns the list of geotags that will be shown in the map.
    - map_element_id: DOM element id where the map will be placed.
    - on_built_callback: function to be called once the map has been built (takes no parameters)
    - on_bounds_changed_callback: function called when the bounds of the map change (because of user interaction). As
        parameters it gets the map ID, updated center latitude, center longitude and zoom, as well as bottom left
        corner latitude and longitude, and top right corner latitude and longitude (see code below for more
        specific details). This callback is also called after map is loaded (bounds are set for the first time).
    - center_lat: latitude where to center the map (if not specified, it is automatically determined based on markers)
    - center_lon: latitude where to center the map (if not specified, it is automatically determined based on markers)
    - zoom: initial zoom for the map (if not specified, it is automatically determined based on markers)
    - show_search: display search bar to fly to places in the map

    This function first calls the Freesound endpoint which returns the list of geotags to be displayed as markers.
    Once the data is received, it creates the map and does all necessary stuff to display it.

    NOTE: the map created using this function is assigned to window.map to make it accessible from everywhere. This is
    needed for the "zoom in" method in info windows. If more than one map is shown in a single page (which does not
    happen in Freesound) the "zoom in" method in inforwindows won't work properly.
     */

    getSoundsLocations(geotags_url, function(data){
        var nSounds = data.length;
        if (nSounds > 0) {  // only if the user has sounds, we render a map

            // Define initial map center and zoom
            var init_zoom = 1;
            var init_lat = 22;
            var init_lon= 24;
            if ((center_lat !== undefined) && (center_lon !== undefined) && (zoom !== undefined)){
                // If center and zoom properties are given, use them to init the map
                init_zoom = zoom;
                init_lat = center_lat;
                init_lon = center_lon;
            }

            // Init map and info window objects
            var map = new mapboxgl.Map({
              container: map_element_id, // HTML container id
              style: 'mapbox://styles/freesound/cjgxefqkb00142roas6kmqneq', // style URL (custom style with satellite and labels)
              center: [init_lon, init_lat], // starting position as [lng, lat]
              zoom: init_zoom,
              maxZoom: 18,
            });
            map.dragRotate.disable();
            map.touchZoomRotate.disableRotation();
            map.addControl(new mapboxgl.NavigationControl({ showCompass: false }));
            if (show_search === true){
                map.addControl(new MapboxGeocoder({ accessToken: mapboxgl.accessToken }), 'top-left');
            }

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
                map.loadImage('/media/images/map_marker.png', function(error, image) {
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
                        clusterRadius: 30 // Radius of each cluster when clustering points (defaults to 50)
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
                                "#007fff",  // 0 to 10
                                10,
                                "#ffad00",  // 10 to 100
                                100,
                                "#ff0006",  // 100 to 1000
                                1000,
                                "#ff00ef"  // 1000+
                            ],
                            "circle-radius": [
                                "step",
                                ["get", "point_count"],
                                12,  // 0 to 10
                                10,
                                16,  // 10 to 100
                                100,
                                18,  // 100 to 1000
                                1000,
                                20  // 1000+
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
                            "text-font": ["Arial Unicode MS Bold"],
                            "text-size": 12
                        }
                    });

                    map.addLayer({
                        id: "sounds-unclustered",
                        type: "symbol",
                        source: "sounds",
                        filter: ["!has", "point_count"],
                        layout: {
                            "icon-image": "custom-marker",
                            "icon-allow-overlap": true,
                        }
                    });

                    // Add popups
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

                    // Adjust map boundaries

                    if (center_lat === undefined){
                        // If initital center and zoom were not given, adjust map boundaries now based on the sounds
                        if (nSounds > 1){
                            map.fitBounds(bounds, {duration:0, padding: {top:40, right:40, left:40, bottom:40}});
                        } else {
                            map.setZoom(4);
                            map.setCenter([geojson_features[0].geometry.coordinates]);
                        }
                    }

                    // Run callback function (if passed) after map is built
                    if (on_built_callback !== undefined){
                        on_built_callback();
                    }

                    // Add listener for callback on bounds changed
                    if (on_bounds_changed_callback !== undefined) {
                        call_on_bounds_chage_callback(map, map_element_id, on_bounds_changed_callback);
                        map.on('moveend', function(e) {
                            call_on_bounds_chage_callback(map, map_element_id, on_bounds_changed_callback);
                        });
                    }
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
    var initial_center = [parseFloat(center_lon, 10), parseFloat(center_lat, 10)];


    var map = new mapboxgl.Map({
      container: map_element_id, // HTML container id
      style: 'mapbox://styles/freesound/cjgxefqkb00142roas6kmqneq', // style URL (custom style with satellite and labels)
      center: initial_center, // starting position as [lng, lat]
      zoom: parseInt(zoom, 10),
      maxZoom: 18,
    });
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }));
    map.addControl(new MapboxGeocoder({ accessToken: mapboxgl.accessToken }), 'top-left');


    map.on('load', function() {
        map.loadImage('/media/images/map_marker.png', function(error, image) {
            map.addImage("custom-marker", image);

            // Add position marker
            map.addLayer({
                id: "position-marker",
                type: "symbol",
                source: {
                    "type": "geojson",
                    "data": {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [center_lon, center_lat]
                        }
                    }
                },
                layout: {
                    "icon-image": "custom-marker",
                    "icon-ignore-placement": true,
                    "icon-allow-overlap": true,
                }
            });


            // Add listener for callback on bounds changed
            if (on_bounds_changed_callback !== undefined) {
                // Initial call to on_bounds_changed_callback
                call_on_bounds_chage_callback(map, map_element_id, on_bounds_changed_callback);
            }
            map.on('move', function(e) {
                if (on_bounds_changed_callback !== undefined) {
                    call_on_bounds_chage_callback(map, map_element_id, on_bounds_changed_callback);
                }
                var new_map_lat = map.getCenter().lat;
                var new_map_lon = map.getCenter().lng;
                map.getSource('position-marker').setData({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [new_map_lon, new_map_lat]
                    }
                });

            });
        });
    });

    return map;
}
