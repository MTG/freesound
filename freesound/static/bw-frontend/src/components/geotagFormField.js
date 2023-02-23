import {makeGeotagEditMap} from '../components/mapsMapbox';


const addGeotagPickerTool = refElement => {
    
    console.log(refElement)
    
    // If Geotag picker tool has not already been displayed, display it
    const wrapperElement = document.createElement('div');
    wrapperElement.className = "v-spacing-3 v-spacing-top-3 text-center";
    const mapElement = document.createElement('div');
    mapElement.id = 'geotag_picker_map';
    mapElement.style.width = '600px';
    mapElement.style.height = '400px';
    mapElement.style.display = 'inline-block';
    const lowerButtonsElement = document.createElement('div');
    lowerButtonsElement.className = 'v-spacing-top-4 v-spacing-2';
    lowerButtonsElement.innerHTML = '<i>latitude, longitude, zoom</i>: <input id="geotag_picker_out" size="24" type="text"></input>';
    const clopyToClipboardElement = document.createElement('a');
    clopyToClipboardElement.className = 'btn-inverse no-hover';
    clopyToClipboardElement.href = 'javascript:void(0)';
    clopyToClipboardElement.onclick = () => {copyValue()};
    clopyToClipboardElement.innerText = 'Copy to clipboard';
    lowerButtonsElement.append(clopyToClipboardElement);
    wrapperElement.append(mapElement)
    wrapperElement.append(lowerButtonsElement)
    refElement.append(wrapperElement);
    window.map = makeGeotagEditMap('geotag_picker_map', showLatLonZoomFields);
    
}

const showLatLonZoomFields = (map_element_id, lat, lon, zoom, box_bl_lat, box_bl_lon, box_tr_lat, box_tr_lon) => {
    const geotagPickerOurElement = document.getElementById('geotag_picker_out');
    geotagPickerOurElement.value = lat.toFixed(6) + ', ' + lon.toFixed(6) + ', ' + zoom.toFixed(0);
}

document.addEventListener("DOMContentLoaded", () => {
    // This need to run in DOMContentLoaded event to make sure mapbxgl scripts have been loaded
    const geotagFieldElements = document.getElementsByClassName("geotag-field");
    geotagFieldElements.forEach(element => {
        addGeotagPickerTool(element);
    });
});
