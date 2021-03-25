import {makeSoundsMap} from '../components/mapsMapbox'

const taps = [...document.querySelectorAll('[data-toggle="tap"]')];
const tapsElements = document.getElementsByClassName('bw-profile__tap_container');

const cleanActiveClass = () => {
  taps.forEach(tap => tap.classList.remove('active'));
  tapsElements.forEach(tapElement =>
    tapElement.classList.remove('bw-profile__tap_container__active')
  );
};

const handleTap = tap => {
  cleanActiveClass();

  const tapContainer = document.getElementById(tap.dataset.target.substring(1));

  tap.classList.add('active');
  tapContainer.classList.add('bw-profile__tap_container__active');
};

taps.forEach(tap => {
  tap.addEventListener('click', () => handleTap(tap));
});


// User geotags map
const mapCanvas = document.getElementById('map_canvas');
const latestGeotagsSection = document.getElementById('latest_geotags');
makeSoundsMap(mapCanvas.dataset.geotagsUrl, 'map_canvas', () => {
  latestGeotagsSection.style.display = 'block'; // Once map is ready, show geotags section
});