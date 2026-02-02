import './page-polyfills';
import { showToast } from '../components/toast';
import { makeSoundsMapWithStaticMapFirst } from '../components/mapsMapbox';

// Share pack button

const toggleShareLinkElement = document.getElementById('toggle-share-link');
const shareLinkElement = document.getElementById('share-link');

const copyShareUrlToClipboard = () => {
  var shareLinkInputElement = shareLinkElement.getElementsByTagName('input')[0];
  shareLinkInputElement.select();
  shareLinkInputElement.setSelectionRange(0, 99999);
  document.execCommand('copy');
  showToast('Pack URL copied in the clipboard');
  document.getSelection().removeAllRanges();
};

const toggleShareLink = () => {
  if (shareLinkElement.style.display === 'none') {
    shareLinkElement.style.display = 'block';
    copyShareUrlToClipboard();
  } else {
    shareLinkElement.style.display = 'none';
  }
};

toggleShareLinkElement.addEventListener('click', toggleShareLink);
shareLinkElement.style.display = 'none';

// Pack geotags map
makeSoundsMapWithStaticMapFirst(
  'pack_geotags',
  'map_canvas',
  'static_map_wrapper'
);
