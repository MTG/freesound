import './page-polyfills';
import {showToast} from '../components/toast';
import {makeSoundsMap} from "../components/mapsMapbox";

// Share pack button

const toggleShareLinkElement = document.getElementById('toggle-share-link');
const shareLinkElement = document.getElementById('share-link');

const copyShareUrlToClipboard = () => {
    var shareLinkInputElement = shareLinkElement.getElementsByTagName("input")[0];
    shareLinkInputElement.select();
    shareLinkInputElement.setSelectionRange(0, 99999);
    document.execCommand("copy");
    showToast('Pack URL copied in the clipboard');
    document.getSelection().removeAllRanges();
}

const toggleShareLink = () => {
    if (shareLinkElement.style.display === "none") {
        shareLinkElement.style.display = "block";
        copyShareUrlToClipboard();
    } else {
        shareLinkElement.style.display = "none";
    }
}

toggleShareLinkElement.addEventListener('click',  toggleShareLink);
shareLinkElement.style.display = "none"

// Pack geotags map
// Load the map only when user clicks on "load map" button
const mapCanvas = document.getElementById('map_canvas');
const geotagsSection = document.getElementById('pack_geotags');
const loadButtonWrapper = document.createElement('div');
const loadMapButton = document.createElement('button');
const loadMap = () => {
    loadMapButton.disabled = true;
    loadMapButton.innerText = 'Loading...'
    if (geotagsSection.getAttribute('data-map-loaded') !== 'true') {
        makeSoundsMap(mapCanvas.dataset.geotagsUrl, 'map_canvas', () => {
            loadButtonWrapper.remove();
            geotagsSection.setAttribute('data-map-loaded', "true");
            mapCanvas.style.display = 'block'; // Once map is ready, show geotags section
        });
    }
}
loadButtonWrapper.id = 'loadMapButtonWrapper';
loadButtonWrapper.classList.add('middle', 'center', 'sidebar-map', 'border-radius-5', 'bg-navy-light-grey', 'w-100');
loadMapButton.onclick = () => {loadMap()};
loadMapButton.classList.add('btn-inverse');
loadMapButton.innerText = 'Load map...';
loadButtonWrapper.appendChild(loadMapButton);
if (geotagsSection !== null){
    geotagsSection.insertBefore(loadButtonWrapper, mapCanvas);
}
