import {makeGeotagEditMap} from '../components/mapsMapbox';
import debounce from 'lodash.debounce';

const setMapPosition = (map, lat, lon, zoom) => {
    map.setZoom(parseInt(zoom, 10) - 1, {'triggeredFromForm': true});
    map.setCenter([parseFloat(lon), parseFloat(lat)], {'triggeredFromForm': true});
};

const showGeotagField = geotagFieldElement => {
    const mapContainer = geotagFieldElement.getElementsByClassName("geotag-picker-map")[0];

    // Decide initial centering for the map
    var center_lat = undefined;
    var center_lon = undefined;
    var zoom = undefined;
    if (mapContainer.dataset.lastLat){
        center_lat = mapContainer.dataset.lastLat;
        center_lon = mapContainer.dataset.lastLon;
        zoom = mapContainer.dataset.lastZoom;
    }
    const mapIdx = mapContainer.dataset.mapIdx;
    const latInputElement = document.getElementsByName(`${mapIdx}-lat`)[0];
    const lonInputElement = document.getElementsByName(`${mapIdx}-lon`)[0];
    const zoomInputElement = document.getElementsByName(`${mapIdx}-zoom`)[0];
    if (latInputElement.value != "" && lonInputElement.value != "" && zoomInputElement.value != ""){
        center_lat = parseFloat(latInputElement.value);
        center_lon = parseFloat(lonInputElement.value);
        zoom = parseInt(zoomInputElement.value);
    }

    // Add map
    const map = makeGeotagEditMap(mapContainer.id, onBoundsChange, center_lat, center_lon, zoom);

    // Add event listeners to update map with form fields
    const debouncedSetMapPosition = debounce(setMapPosition);
    [latInputElement, lonInputElement, zoomInputElement].forEach(element => {
        element.addEventListener('input', evt => {
            debouncedSetMapPosition(map, latInputElement.value, lonInputElement.value, zoomInputElement.value);
        });
    })

    // Handle button for removing geolocation information
    const removeGeotagCheckbox = document.getElementsByName(`${mapIdx}-remove_geotag`)[0];
    removeGeotagCheckbox.value = false; 
    const removeGeolocationButton = geotagFieldElement.getElementsByClassName('remove-geolocation-button')[0];
    removeGeolocationButton.addEventListener('click', evt => {
        evt.preventDefault(); // Don't submit form
        const geotagFieldWrapper = geotagFieldElement.getElementsByClassName("geotag-field-wrapper")[0];
        geotagFieldWrapper.classList.add('display-none');
        const buttonElement = geotagFieldElement.getElementsByTagName('button')[0];
        buttonElement.classList.remove('display-none');
        const removeGeotagCheckbox = document.getElementsByName(`${mapIdx}-remove_geotag`)[0];
        removeGeotagCheckbox.value = true;
        latInputElement.value = "";
        lonInputElement.value = "";
        zoomInputElement.value = "";
    });
}

const onBoundsChange = (map_container_id, lat, lon, zoom, box_bl_lat, box_bl_lon, box_tr_lat, box_tr_lon) => {
    const mapIdx = document.getElementById(map_container_id).dataset.mapIdx;
    const latInputElement = document.getElementsByName(`${mapIdx}-lat`)[0];
    const lonInputElement = document.getElementsByName(`${mapIdx}-lon`)[0];
    const zoomInputElement = document.getElementsByName(`${mapIdx}-zoom`)[0];
    latInputElement.value = lat.toFixed(6);
    lonInputElement.value = lon.toFixed(6);
    zoomInputElement.value = zoom.toFixed(0);
}

const showGeotagFieldAndRemoveShowButton = (geotagFieldElement, buttonElement) => {
    const geotagFieldWrapper = geotagFieldElement.getElementsByClassName("geotag-field-wrapper")[0];
    geotagFieldWrapper.classList.remove('display-none');
    showGeotagField(geotagFieldElement);
    buttonElement.classList.add('display-none');
};

document.addEventListener("DOMContentLoaded", () => {
    // This need to run in DOMContentLoaded event to make sure mapbxgl scripts have been loaded
    const showGeolocationButtons = document.getElementsByClassName("show-geolocation-button");
    showGeolocationButtons.forEach(buttonElement => {
        const geotagFieldElement = buttonElement.parentNode;
        if (geotagFieldElement.dataset.hasGeotag){
            showGeotagFieldAndRemoveShowButton(geotagFieldElement, buttonElement);
        } else {
            buttonElement.addEventListener('click', evt => {
                evt.preventDefault(); // Don't submit form
                showGeotagFieldAndRemoveShowButton(geotagFieldElement, buttonElement);
            });
        }
    });
});
