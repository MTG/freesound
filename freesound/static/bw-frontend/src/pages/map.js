import { makeSoundsMap } from '../components/mapsMapbox';

const loadingIndicator = document.getElementById('mapLoadingIndicator');
const embedControls = document.getElementById('embedControls');
const embedControlsLabel = document.getElementById('embedControlsLabel');
const embedCodeElement = document.getElementById('embedCode');
const embedClusterCheckElement = document.getElementById('embedClusterCheck');
const embedWidthInputElement = document.getElementById('embedWidthInput');
const embedHeightInputElement = document.getElementById('embedHeightInput');
const tagFilterInput = document.getElementById('tagFilter');

let currentLat;
let currentLon;
let currentZoom;

const toggleEmbedControls = () => {
  if (embedControls.classList.contains('display-none')) {
    embedControls.classList.remove('display-none');
    embedControlsLabel.innerText = 'Hide embed options';
  } else {
    embedControls.classList.add('display-none');
    embedControlsLabel.innerText = 'Embed this map';
  }
};

const updateQueryStringParameter = (uri, key, value) => {
  var re = new RegExp('([?&])' + key + '=.*?(&|#|$)', 'i');
  if (uri.match(re)) {
    return uri.replace(re, '$1' + key + '=' + value + '$2');
  } else {
    var hash = '';
    if (uri.indexOf('#') !== -1) {
      hash = uri.replace(/.*#/, '#');
      uri = uri.replace(/#.*/, '');
    }
    var separator = uri.indexOf('?') !== -1 ? '&' : '?';
    return uri + separator + key + '=' + value + hash;
  }
};

const updateEmbedCode = (mapElementId, lat, lon, zoom) => {
  if (embedCodeElement === null) {
    return;
  }
  let mapCanvas;
  if (mapElementId === undefined) {
    mapCanvas = document.getElementsByClassName('main-map')[0];
  } else {
    mapCanvas = document.getElementById(mapElementId);
  }

  // Store lat, lon and zoom globally so we can use them later to call updateEmbedCode without accessing map
  currentLat = lat;
  currentLon = lon;
  currentZoom = zoom;

  // Generate embed code
  const width = parseInt(embedWidthInputElement.value, 10);
  const height = parseInt(embedHeightInputElement.value, 10);
  let cluster = 'on';
  if (!embedClusterCheckElement.checked) {
    cluster = 'off';
  }
  let embedCode =
    '<iframe frameborder="0" scrolling="no" src="' +
    mapCanvas.dataset.geotagsEmbedBaseUrl +
    '?c_lat=' +
    lat +
    '&c_lon=' +
    lon +
    '&z=' +
    zoom +
    '&c=' +
    cluster +
    '&w=' +
    width +
    '&h=' +
    height;
  if (mapCanvas.dataset.mapUsername !== '') {
    embedCode += '&username=' + mapCanvas.dataset.mapUsername;
  }
  if (mapCanvas.dataset.mapTag !== '') {
    embedCode += '&tag=' + mapCanvas.dataset.mapTag;
  }
  if (mapCanvas.dataset.mapPackId !== '') {
    embedCode += '&pack=' + mapCanvas.dataset.mapPackId;
  }
  if (mapCanvas.dataset.mapQp !== '') {
    embedCode += '&qp=' + mapCanvas.dataset.mapQp;
  }
  embedCode += '" width="' + width + '" height="' + height + '"></iframe>';
  embedCodeElement.innerText = embedCode;

  // Update page URL so it can directly be used to share the map
  let newUrl = window.location.href;
  newUrl = updateQueryStringParameter(newUrl, 'c_lat', lat);
  newUrl = updateQueryStringParameter(newUrl, 'c_lon', lon);
  newUrl = updateQueryStringParameter(newUrl, 'z', zoom);
  window.history.replaceState({}, document.title, newUrl);
};

const changeEmbedWidthHeightCluster = () => {
  updateEmbedCode(undefined, currentLat, currentLon, currentZoom);
};

const initMap = mapCanvas => {
  // Avoid initializing a map twice
  if (mapCanvas.dataset.initialized === 'true') {
    return;
  }
  mapCanvas.dataset.initialized = 'true';

  // Configure some event listeners

  if (embedControlsLabel !== null) {
    embedControlsLabel.addEventListener('click', () => {
      toggleEmbedControls();
    });
  }

  [
    embedWidthInputElement,
    embedHeightInputElement,
    embedClusterCheckElement,
  ].forEach(element => {
    if (element !== null) {
      element.addEventListener('change', () => {
        changeEmbedWidthHeightCluster();
      });
    }
  });

  if (tagFilterInput !== null) {
    tagFilterInput.addEventListener('keypress', e => {
      if (e.key === 'Enter') {
        // Submit query filter
        const tag = tagFilterInput.value.replace(/[^A-Za-z0-9-_]/g, ''); // Only allow alphanumeric plus - _
        const includeLatLonZoom = false;
        let url = `${tagFilterInput.dataset.baseUrl + tag}/`;
        if (includeLatLonZoom) {
          url += `?c_lat=${currentLat}&c_lon=${currentLon}&z=${currentZoom}`;
        }
        window.location = url;
        e.stopPropagation();
      }
    });
  }

  // Do proper map initialization
  let centerLat;
  let centerLon;
  let zoom;
  if (
    mapCanvas.dataset.mapCenterLat !== 'None' &&
    mapCanvas.dataset.mapCenterLon !== 'None' &&
    mapCanvas.dataset.mapZoom !== 'None'
  ) {
    centerLat = mapCanvas.dataset.mapCenterLat;
    centerLon = mapCanvas.dataset.mapCenterLon;
    zoom = mapCanvas.dataset.mapZoom;
  }
  let url = mapCanvas.dataset.geotagsUrl;
  const showSearch =
    mapCanvas.dataset.mapShowSearch !== undefined &&
    mapCanvas.dataset.mapShowSearch === 'true';
  const showStyleSelector = true;
  const clusterGeotags = true;
  const showMapEvenIfNoGeotags = true;

  makeSoundsMap(
    url,
    mapCanvas.id,
    numLoadedSounds => {
      if (loadingIndicator !== null) {
        loadingIndicator.innerText = `${numLoadedSounds} sound${numLoadedSounds === 1 ? '' : 's'}`;
      }
      if (embedWidthInputElement !== null) {
        embedWidthInputElement.value = mapCanvas.offsetWidth;
        embedHeightInputElement.value = mapCanvas.offsetHeight;
      }
    },
    updateEmbedCode,
    centerLat,
    centerLon,
    zoom,
    showSearch,
    showStyleSelector,
    clusterGeotags,
    showMapEvenIfNoGeotags
  );
};

export { initMap };
