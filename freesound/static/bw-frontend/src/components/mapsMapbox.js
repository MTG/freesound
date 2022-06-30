import {stopAllPlayers} from './player/utils'
import {createPlayer} from './player/player-ui'


var FREESOUND_SATELLITE_STYLE_ID = 'cjgxefqkb00142roas6kmqneq';
var FREESOUND_STREETS_STYLE_ID = 'cjkmk0h7p79z32spe9j735hrd';
var MIN_INPUT_CHARACTERS_FOR_GEOCODER =  3; // From mapbox docs: "Minimum number of characters to enter before [geocoder] results are shown"
var MAP_MARKER_URL = '/static/bw-frontend/public/map_marker.png'; 
var MAP_MARKER_2X_URL = '/static/bw-frontend/public/map_marker_2x.png';

function setMaxZoomCenter(lat, lng, zoom) {
    window.map.flyTo({'center': [lng, lat], 'zoom': zoom - 1});  // Subtract 1 for compatibility with gmaps zoom levels
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
        map.getZoom() + 1,  // Add 1 for compatibility with gmaps zoom levels
        map.getBounds().getSouthWest().lat,  // Latidude (at bottom left of map)
        map.getBounds().getSouthWest().lng,  // Longitude (at bottom left of map)
        map.getBounds().getNorthEast().lat,  // Latidude (at top right of map)
        map.getBounds().getNorthEast().lng   // Longitude (at top right  of map)
    )
}

function toggleMapStyle(idx){

    if (window.map !== undefined){
        var map = window.map;
    } else {
        // if idx is passed, it means map objects will have been saved in maps variable
        var map = window.maps[idx];
    }

    var mapElementId = map.getCanvas().parentElement.parentElement.id;
    const mapElement = document.getElementById(mapElementId);

    if (map.getStyle().sprite.indexOf(FREESOUND_STREETS_STYLE_ID) !== -1){
        // Using streets map, switch to satellite
        map.setStyle('mapbox://styles/freesound/' + FREESOUND_SATELLITE_STYLE_ID);
        mapElement.getElementsByClassName('map_terrain_menu').forEach(element => {
            element.innerText = 'Show streets';
        });

    } else {
        // Using satellite map, switch to streets
        map.setStyle('mapbox://styles/freesound/' + FREESOUND_STREETS_STYLE_ID);
        mapElement.getElementsByClassName('map_terrain_menu').forEach(element => {
            element.innerText = 'Show terrain';
        });
    }
}

function latLonZoomAreValid(lat, lon, zoom){
    return !(isNaN(lat) || (isNaN(lon)) || (isNaN(zoom) || lat === '' || lon === '' || zoom === ''))
}

function clipLatLonRanges(lat, lon){
    if ((lat < -90)){
        lat = -90;
    } else if ((lat > 90)){
        lat = 90;
    }
    if ((lon < -180)){
        lon = -180;
    } else if ((lon > 180)){
        lon = 180;
    }

    return [lat, lon];
}

function ajaxLoad(url, callback, postData, plain) {
    var http_request = false;

    if (window.XMLHttpRequest) { // Mozilla, Safari, ...
        http_request = new XMLHttpRequest();
        if (http_request.overrideMimeType && plain) {
            http_request.overrideMimeType('text/plain');
        }
    } else if (window.ActiveXObject) { // IE
        try {
            http_request = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {
            try {
                http_request = new ActiveXObject("Microsoft.XMLHTTP");
            } catch (e) {}
        }
    }
    if (!http_request) {
        console.log('Giving up :( Cannot create an XMLHTTP instance');
        return false;
    }
    http_request.onreadystatechange =  function() {
        if (http_request.readyState == 4) {
            if (http_request.status == 200) {
                eval(callback(http_request));
            }
            else {
                conosle.log('Request Failed: ' + http_request.status);
            }
        }
    };

    if (postData) { // POST
        http_request.open('POST', url, true);
        http_request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        http_request.setRequestHeader("Content-length", postData.length);
        http_request.send(postData);
    }
    else {
        http_request.open('GET', url, true);
        http_request.send(null);
    }
}

function makeSoundsMap(geotags_url, map_element_id, on_built_callback, on_bounds_changed_callback,
                       center_lat, center_lon, zoom, show_search, show_style_selector, cluster, show_if_empty){
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
    - show_terrain_selector: display button to switch between streets and satellite styles
    - cluster: whether or not to perform point clustering (on by default)
    - show_if_empty: show map even if there are no geotags to show

    This function first calls the Freesound endpoint which returns the list of geotags to be displayed as markers.
    Once the data is received, it creates the map and does all necessary stuff to display it.

    NOTE: the map created using this function is assigned to window.map to make it accessible from everywhere. This is
    needed for the "zoom in" method in info windows. If more than one map is shown in a single page (which does not
    happen in Freesound) the "zoom in" method in inforwindows won't work properly.
     */

    getSoundsLocations(geotags_url, function(data){
        var nSounds = data.length;
        if ((nSounds > 0) || show_if_empty) {

            // Define initial map center and zoom
            var init_zoom = 2;
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
              style: 'mapbox://styles/freesound/' + FREESOUND_SATELLITE_STYLE_ID, // style URL
              center: [init_lon, init_lat], // starting position as [lng, lat]
              zoom: init_zoom - 1,  // Subtract 1 for compatibility with gmaps zoom levels
              maxZoom: 18,
            });
            map.dragRotate.disable();
            map.touchZoomRotate.disableRotation();
            map.addControl(new mapboxgl.NavigationControl({ showCompass: false }));
            if (show_search === true){
                map.addControl(new MapboxGeocoder({ accessToken: mapboxgl.accessToken, minLength: MIN_INPUT_CHARACTERS_FOR_GEOCODER}), 'top-left');
            }
            window.map = map; // Used to have a global reference to the map

            // Get coordinates for each sound
            var geojson_features = [];
            var bounds = new mapboxgl.LngLatBounds();

            data.forEach(item => {
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
                const mapElement = document.getElementById(map_element_id);

                // Add satellite/streets controls
                if (show_style_selector === true) {
                    const styleSelectorElement = document.createElement('div');
                    styleSelectorElement.className = "map_terrain_menu";
                    styleSelectorElement.onclick = () => {toggleMapStyle()};
                    styleSelectorElement.innerHTML = "Show streets"
                    mapElement.append(styleSelectorElement);
                }

                // Add popups
                map.on('click', 'sounds-unclustered', function (e) {

                    stopAllPlayers();
                    var coordinates = e.features[0].geometry.coordinates.slice();
                    var sound_id = e.features[0].properties.id;
                    let url = '/geotags/infowindow/' + sound_id;
                    if (document.getElementById(map_element_id).offsetWidth < 500){
                        // If map is small, use minimal info windows
                        url += '/?minimal=1'
                    }
                    ajaxLoad(url , function(data, responseCode)
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

                        // Zoom to position on "zoom in" click
                        const zoomLinkElement = document.getElementById('infoWindowZoomLink-' + sound_id);
                        zoomLinkElement.onclick = () => {setMaxZoomCenter(zoomLinkElement.dataset.lat, zoomLinkElement.dataset.lon, zoomLinkElement.dataset.zoom)};

                        // Stop sound on popup close
                        popup.on('close', function(e) {
                            stopAllPlayers();
                        });

                        // Init sound player inside popup
                        const playerWrapper = document.getElementById('infoWindowPlayerWrapper-' + sound_id);
                        const players = [...playerWrapper.getElementsByClassName('bw-player')]
                        players.forEach(createPlayer)
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

                // Zoom-in when clicking on clusters
                map.on('click', 'sounds-clusters', function (e) {
                    map.flyTo({'center': e.lngLat, 'zoom': map.getZoom() + 4});
                });

                // Adjust map boundaries
                if (center_lat === undefined){
                    // If initital center and zoom were not given, adjust map boundaries now based on the sounds
                    if (nSounds > 1){
                        // The padding and offset "manual" adjustments of bounds below are to make the boudns more similar to
                        // those created in the mapbox static maps
                        map.fitBounds(bounds, {duration:0, offset:[-10, 0],  padding: {top:60, right:60, left:0, bottom:50}});
                    } else {
                        map.setZoom(3);
                        if (nSounds > 0){
                            map.setCenter(geojson_features[0].geometry.coordinates);
                        }
                    }
                }

                // Run callback function (if passed) after map is built
                if (on_built_callback !== undefined){
                    on_built_callback(nSounds);
                }

                // Add listener for callback on bounds changed
                if (on_bounds_changed_callback !== undefined) {
                    call_on_bounds_chage_callback(map, map_element_id, on_bounds_changed_callback);
                    map.on('moveend', function(e) {
                        call_on_bounds_chage_callback(map, map_element_id, on_bounds_changed_callback);
                    });
                }
            });


            map.on('style.load', function () {  // Triggered when `setStyle` is called, add all data layers
                map.loadImage(MAP_MARKER_URL, function(error, image) {
                    map.addImage("custom-marker", image);

                    // Setup clustering
                    if (cluster === undefined){
                        cluster = true;
                    }

                    // Add a new source from our GeoJSON data and set the
                    // 'cluster' option to true. GL-JS will add the point_count property to your source data.
                    map.addSource("sounds", {
                        type: "geojson",
                        data: {
                            "type": "FeatureCollection",
                            "features": geojson_features
                        },
                        cluster: cluster,
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
                                "#1d9fb5",  // 0 to 10
                                10,
                                "#1cae48",  // 10 to 100
                                100,
                                "#ff9e35",  // 100 to 1000
                                1000,
                                "#ff3546"  // 1000+
                            ],
                            "circle-radius": [
                                "step",
                                ["get", "point_count"],
                                12,  // 0 to 10
                                10,
                                14,  // 10 to 100
                                100,
                                16,  // 100 to 1000
                                1000,
                                18  // 1000+
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
                });
            });
        }
    });
}


function makeGeotagEditMap(map_element_id, on_bounds_changed_callback, center_lat, center_lon, zoom, idx){

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
    - idx: map idx (used when creating multiple maps)

    This function returns the object of the map that has been created.
     */

    // Initialize map
    if (center_lat === undefined){  // Load default center
        center_lat = 23.8858;
        center_lon = 21.7968;
        zoom = 1;
    }
    var initial_center = [parseFloat(center_lon, 10), parseFloat(center_lat, 10)];
    var map = new mapboxgl.Map({
      container: map_element_id, // HTML container id
      style: 'mapbox://styles/freesound/cjgxefqkb00142roas6kmqneq', // style URL (custom style with satellite and labels)
      center: initial_center, // starting position as [lng, lat]
      zoom: parseInt(zoom, 10) - 1,  // Subtract 1 for compatibility with gmaps zoom levels
      maxZoom: 18,
        maxBounds: [[-360,-90],[360,90]]
    });
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }));
    map.addControl(new MapboxGeocoder({ accessToken: mapboxgl.accessToken, minLength: MIN_INPUT_CHARACTERS_FOR_GEOCODER }), 'top-left');

    map.on('load', function() {
        // Add controls for toggling style
        const mapElement = document.getElementById(map_element_id);

        const styleSelectorElement = document.createElement('div');
        styleSelectorElement.className = "map_terrain_menu";
        styleSelectorElement.onclick = () => {toggleMapStyle(idx)};
        styleSelectorElement.innerHTML = "Show streets"
        mapElement.append(styleSelectorElement);

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

    map.on('style.load', function () {  // Triggered when `setStyle` is called, add all data layers
        map.loadImage(MAP_MARKER_URL, function(error, image) {
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

            // Update marker
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

    return map;
}

const makeStaticMap = (mapWrapperElementId, width, height, onclick) => {
    const mapWrapperElement = document.getElementById(mapWrapperElementId);
    const token = mapboxgl.accessToken;
    const padding = 40;
    const pins = [];
    JSON.parse(mapWrapperElement.dataset.pins).forEach( pin => {
        pins.push(`url-https://freesound.org${MAP_MARKER_2X_URL}(${pin.lon},${pin.lat})`)
    });
    const imageUrl = `https://api.mapbox.com/styles/v1/freesound/${FREESOUND_SATELLITE_STYLE_ID}/static/${encodeURIComponent(pins.join(','))}/auto/${width}x${height}@2x?padding=${padding}%2C${padding}%2C${padding}%2C${padding}&access_token=${token}`;
    mapWrapperElement.style.background = `url("${imageUrl}")`;
    mapWrapperElement.style.backgroundSize = 'cover';
    mapWrapperElement.addEventListener('click', () => {
        onclick();
    });
}

/**
 * @param {string} mainWrapperElementId
 * @param {string} mapCanvasId
 * @param {string} staticMapWrapperElementId
 */
const makeSoundsMapWithStaticMapFirst = (mainWrapperElementId, mapCanvasId, staticMapWrapperElementId) => {
    // Load the map only when user clicks on "load map" button (or when clicking on static map image if using static map images)
    const mapCanvas = document.getElementById(mapCanvasId);
    const staticMapWrapper = document.getElementById(staticMapWrapperElementId);
    const mainWrapperElement = document.getElementById(mainWrapperElementId);
    const loadButtonWrapper = document.createElement('div');

    const loadMapButton = document.createElement('button');
    const loadMap = () => {
    loadMapButton.disabled = true;
    loadMapButton.innerText = 'Loading...'
    if (mainWrapperElement.getAttribute('data-map-loaded') !== 'true') {
        makeSoundsMap(mapCanvas.dataset.geotagsUrl, 'map_canvas', () => {
            if (staticMapWrapper !== null){
                staticMapWrapper.remove();
            }
            if (loadButtonWrapper !== null){
                loadButtonWrapper.remove();
            }
            mainWrapperElement.setAttribute('data-map-loaded', "true");
            mapCanvas.style.display = 'block'; // Once map is ready, show geotags section
            }, undefined, undefined, undefined, undefined, undefined, undefined, false);
    }
    }
    loadButtonWrapper.id = 'loadMapButtonWrapper';
    loadButtonWrapper.classList.add('middle', 'center', 'sidebar-map', 'border-radius-5', 'bg-navy-light-grey', 'w-100');
    loadMapButton.onclick = () => {loadMap()};
    loadMapButton.classList.add('btn-inverse');
    loadMapButton.innerText = 'Load map...';
    if (mainWrapperElement !== null){
    if (staticMapWrapper !== null){
        makeStaticMap('static_map_wrapper', 300, 300, () => {
        loadMapButton.style.backgroundColor = "white";
        staticMapWrapper.appendChild(loadMapButton);
        loadMap();
        })
    } else {
        loadButtonWrapper.appendChild(loadMapButton);
        mainWrapperElement.insertBefore(loadButtonWrapper, mapCanvas);
    }
    }
}


export {makeSoundsMap, makeGeotagEditMap, makeSoundsMapWithStaticMapFirst};