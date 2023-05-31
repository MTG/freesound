import './page-polyfills';
import {showToast} from '../components/toast';
import {makeSoundsMapWithStaticMapFirst} from "../components/mapsMapbox";
import {handleDownloadersModal} from "../components/downloadersModals";

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
makeSoundsMapWithStaticMapFirst('pack_geotags', 'map_canvas', 'static_map_wrapper')

// Open downloaders modal if activation parameter is passed
const urlParams = new URLSearchParams(window.location.search);
const downloadersButtons = document.querySelectorAll('[data-toggle="downloaders-modal"]');
if (downloadersButtons.length > 0){
    const downloadersModalActivationParam = downloadersButtons[0].dataset.modalActivationParam;
    const downloadersModalParamValue = urlParams.get(downloadersModalActivationParam);
    if (downloadersModalParamValue) {
        handleDownloadersModal(downloadersButtons[0].dataset.modalContentUrl, downloadersModalActivationParam, downloadersModalParamValue);
    }
}
