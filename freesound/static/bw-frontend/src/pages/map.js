import {makeSoundsMap} from '../components/mapsMapbox';

const loadingIndicator = document.getElementById("indicator");
const mapCanvas = document.getElementById('mapCanvas');
const embedControls = document.getElementById("embedControls");
const embedControlsLabel = document.getElementById("embedControlsLabel");
const embedCodeElement = document.getElementById("embedCode");
const embedClusterCheckElement = document.getElementById("embedClusterCheck");
const embedWidthInputElement = document.getElementById("embedWidthInput");
const embedHeightInputElement = document.getElementById("embedHeightInput");
const tagFilterInput = document.getElementById("tagFilter");

let currentLat;
let currentLon;
let currentZoom;
let currentBoxBlLa;
let currentBoxBlLon;
let currentBoxTrLat;
let currentBoxTrLon;

let centerLat;
let centerLon;
let zoom;
const showSearch = true;
const showStyleSelector = true;

const toggleEmbedControls = () => {
    if (embedControls.classList.contains('display-none')){
        embedControls.classList.remove('display-none');
        embedControls.classList.add('display-inline-block');
        embedControlsLabel.innerText = "Hide embed options";
    } else{
        embedControls.classList.remove('display-inline-block');
        embedControls.classList.add('display-none');
        embedControlsLabel.innerText = "Embed this map";
    }
};

embedControlsLabel.addEventListener('click', () => {
    toggleEmbedControls();
});

const updateQueryStringParameter = (uri, key, value) => {
    var re = new RegExp("([?&])" + key + "=.*?(&|#|$)", "i");
    if (uri.match(re)) {
        return uri.replace(re, '$1' + key + "=" + value + '$2');
    } else {
        var hash =  '';
        if( uri.indexOf('#') !== -1 ){
            hash = uri.replace(/.*#/, '#');
            uri = uri.replace(/#.*/, '');
        }
        var separator = uri.indexOf('?') !== -1 ? "&" : "?";
        return uri + separator + key + "=" + value + hash;
    }
}

const updateEmbedCode = (_, lat, lon, zoom, boxBlLat, boxBlLon, boxTrLat, boxTrLon) => {
    // Store lat, lon and zoom globally so we can use them later to call updateEmbedCode without accessing map
    currentLat = lat;
    currentLon = lon;
    currentZoom = zoom;
    currentBoxBlLa = boxBlLat;
    currentBoxBlLon = boxBlLon;
    currentBoxTrLat = boxTrLat;
    currentBoxTrLon = boxTrLon;

    // Generate embed code
    const box = "#box=" + boxBlLat + "," + boxBlLon+"," + boxTrLat+"," + boxTrLon;
    const width = parseInt(embedWidthInputElement.value, 10);
    const height = parseInt(embedHeightInputElement.value, 10);
    let cluster = 'on';
    if (!embedClusterCheckElement.checked){
        cluster = 'off';
    }
    let embedCode = "<iframe frameborder=\"0\" scrolling=\"no\" src=\"" + mapCanvas.dataset.geotagsEmbedBaseUrl
        + "?c_lat=" + lat + "&c_lon=" + lon + "&z=" + zoom + "&c=" + cluster + "&w=" + width + "&h=" + height;
    if (mapCanvas.dataset.mapUsername !== "None"){
        embedCode += "&username={{ username }}";
    }
    if (mapCanvas.dataset.mapTag !== "None"){
        embedCode += "&tag={{ tag }}";
    }
    embedCode += box + "\" width=\"" + width + "\" height=\"" + height + "\"></iframe>";
    embedCodeElement.innerText = embedCode;

    // Update page URL so it can directly be used to share the map
    let newUrl = window.location.href;
    newUrl = updateQueryStringParameter(newUrl, 'c_lat', lat);
    newUrl = updateQueryStringParameter(newUrl, 'c_lon', lon);
    newUrl = updateQueryStringParameter(newUrl, 'z', zoom);
    window.history.replaceState( {} , document.title, newUrl );
}

const changeEmbedWidthHeightCluster = () => {
    updateEmbedCode(undefined, currentLat, currentLon, currentZoom, currentBoxBlLa, currentBoxBlLon, currentBoxTrLat, currentBoxTrLon);
}

[embedWidthInputElement, embedHeightInputElement, embedClusterCheckElement].forEach(element => {
    element.addEventListener('change', () => {
       changeEmbedWidthHeightCluster();
    });
});

if (tagFilterInput !== null){
    tagFilterInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            // Submit query filter
            const tag = tagFilterInput.value;
            const url = `${tagFilterInput.dataset.baseUrl + tag}/?c_lat=${currentLat}&c_lon=${currentLon}&z=${currentZoom}`;
            window.location = url;
        }
        e.stopPropagation();
    });
}

if ((mapCanvas.dataset.mapCenterLat !== "None") &&
    (mapCanvas.dataset.mapCenterLon !== "None") &&
    (mapCanvas.dataset.mapZoom !== "None")){
    centerLat = mapCanvas.dataset.mapCenterLat;
    centerLon = mapCanvas.dataset.mapCenterLon;
    zoom = mapCanvas.dataset.mapZoom;
}
let url = mapCanvas.dataset.geotagsUrl;
const urlBox = mapCanvas.dataset.geotagsUrlBox;
const box = document.location.hash.slice(5, document.location.hash.length);
if (box !== ''){
    // If box is given, get the geotags only from that box
     url = `${urlBox}?box=${box}`;
}

makeSoundsMap(url, 'mapCanvas', () => {
  loadingIndicator.style.display = 'none';
}, updateEmbedCode, centerLat, centerLon, zoom, showSearch, showStyleSelector);
