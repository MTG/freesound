// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import {makeGeotagEditMap} from '../components/mapsMapbox';
import {showToast} from "./toast";

const showGeotagPickerHelpTool = refElementID => {
    const geotagPickerMapElement = document.getElementById('geotag_picker_map');
    const refElement = document.getElementById(refElementID);

    if (geotagPickerMapElement !== undefined){
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
}

const showLatLonZoomFields = (map_element_id, lat, lon, zoom, box_bl_lat, box_bl_lon, box_tr_lat, box_tr_lon) => {
    const geotagPickerOurElement = document.getElementById('geotag_picker_out');
    geotagPickerOurElement.value = lat.toFixed(6) + ', ' + lon.toFixed(6) + ', ' + zoom.toFixed(0);
}

const copyValue = () => {
    const geotagPickerOurElement = document.getElementById('geotag_picker_out');
    geotagPickerOurElement.select();
    geotagPickerOurElement.setSelectionRange(0, 99999);
    document.execCommand("copy");
    showToast('Geotag copied in the clipboard');
    document.getSelection().removeAllRanges();
}

document.addEventListener("DOMContentLoaded", () => {
    const showGeotagPickerElements = document.getElementsByClassName("show-geotag-picker");
    showGeotagPickerElements.forEach(element => {
        element.setAttribute('onclick', '');
        element.addEventListener('click', () => {
            showGeotagPickerHelpTool(element.dataset.refElementId);
        });
    });
});

// @license-end
