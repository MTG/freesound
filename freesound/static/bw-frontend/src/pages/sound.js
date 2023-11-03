import './page-polyfills';
import {showToast} from '../components/toast';
import {playAtTime} from '../components/player/utils';
import {handleGenericModalWithForm} from '../components/modal';
import {addRecaptchaScriptTagToMainHead} from '../utils/recaptchaDynamicReload'
import { prepareAfterDownloadSoundModals } from '../components/afterDownloadModal.js';

const toggleEmbedCodeElement = document.getElementById('toggle-embed-code');
const toggleShareLinkElement = document.getElementById('toggle-share-link');
const embedLinksElement = document.getElementById('embed-links');
const embedCodeElement = document.getElementById('embed-code');
const smallEmbedImageElement = document.getElementById('small-embed-image');
const mediumEmbedImageElement = document.getElementById('medium-embed-image');
const largeEmbedImageElement = document.getElementById('large-embed-image');
const shareLinkElement = document.getElementById('share-link');
const urlParams = new URLSearchParams(window.location.search);

prepareAfterDownloadSoundModals();

const copyShareUrlToClipboard = () => {
    var shareLinkInputElement = shareLinkElement.getElementsByTagName("input")[0];
    shareLinkInputElement.select();
    shareLinkInputElement.setSelectionRange(0, 99999);
    document.execCommand("copy");
    showToast('Sound URL copied in the clipboard');
    document.getSelection().removeAllRanges();
}

const toggleEmbedCode = () => {
    if (embedLinksElement.style.display === "none") {
        embedLinksElement.style.display = "block";
    } else {
        embedLinksElement.style.display = "none";
    }
    
    if (shareLinkElement.style.display !== "none") {
        shareLinkElement.style.display = "none";
    }
}

const toggleShareLink = () => {
    if (shareLinkElement.style.display === "none") {
        shareLinkElement.style.display = "block";
        copyShareUrlToClipboard();
    } else {
        shareLinkElement.style.display = "none";
    }
    
    if (embedLinksElement.style.display !== "none") {
        embedLinksElement.style.display = "none";
    }
}

toggleEmbedCodeElement.addEventListener('click',  toggleEmbedCode);
toggleShareLinkElement.addEventListener('click',  toggleShareLink);


const generateEmbedCode = (size) => {
    var sizes = embedCodeElement.dataset['size' + size].split(',');
    var urlTemplate = embedCodeElement.dataset.iframeUrlTemplate;
    var embedText = '<iframe frameborder="0" scrolling="no" src="' + urlTemplate + '" width="WIDTH" height="HEIGHT"></iframe>';
    embedText = embedText.replace('SIZE', size.toLowerCase());
    embedText = embedText.replace('WIDTH', sizes[0]);
    embedText = embedText.replace('HEIGHT', sizes[1]);
    embedCodeElement.value = embedText;
}

smallEmbedImageElement.addEventListener('click',  () => generateEmbedCode('Small'));
mediumEmbedImageElement.addEventListener('click', () => generateEmbedCode('Medium'));
largeEmbedImageElement.addEventListener('click', () => generateEmbedCode('Large'));

embedLinksElement.style.display = "none"
shareLinkElement.style.display = "none"

// Transform time marks in sound description and comments into playable timestamps
const audioElement = document.getElementsByTagName('audio')[0];

const findTimeLinksAndAddEventListeners = element => {
    // Replace timestamps of pattern #m:ss (e.g. #0:36) for anchor with a specific class and play icon
    const playIconHtml = '<span class="bw-icon-play" style="font-size:70%"></span>';
    element.innerHTML = element.innerHTML.replaceAll(/#\d+:\d+/g, '<a class="play-at-time" href="javascript:void(0);">' + playIconHtml + '$&</a>');
    element.innerHTML = element.innerHTML.replaceAll(playIconHtml + '#', playIconHtml);
    // Add listener events to each of the created anchors
    element.getElementsByClassName('play-at-time').forEach(playAyTimeElement => {
        playAyTimeElement.addEventListener('click', (e) => {
            if (!e.altKey){
                const seconds = parseInt(playAyTimeElement.innerText.split(':')[0], 10) * 60 + parseInt(playAyTimeElement.innerText.split(':')[1], 10);
                playAtTime(audioElement, seconds);
            } else {
                audioElement.pause();
            }
        });
    });
};

const soundDescriptionElement = document.getElementById('soundDescriptionSection');
const soundCommentsSection = document.getElementById('soundCommentsSection');
const soundCommentElements = soundCommentsSection.getElementsByTagName('p');

soundCommentElements.forEach(element => {
    findTimeLinksAndAddEventListeners(element);
});

findTimeLinksAndAddEventListeners(soundDescriptionElement);

// Open flag sound modal if activation parameter is passed
const flagSoundButton = [...document.querySelectorAll('[data-toggle^="flag-sound-modal"]')][0];
const flagSoundModalActivationParam = flagSoundButton.dataset.modalActivationParam;
const flagSoundModalParamValue = urlParams.get(flagSoundModalActivationParam);

const initSoundFlagForm = (modalContainer) => {
    // Modify the form structure to add a "Reason type:" label inline with the select dropdown
    const selectElement = modalContainer.getElementsByTagName('select')[0];
    const wrapper = document.createElement('div');
    wrapper.style = 'display:inline-block;';
    selectElement.parentNode.insertBefore(wrapper, selectElement);
    const label = document.createElement('div');
    label.innerHTML = "Reason type:"
    label.classList.add('text-grey');
    wrapper.appendChild(label)
    wrapper.appendChild(selectElement)
    
    // Init recaptcha fields
    const form = modalContainer.getElementsByTagName('form')[0];
    addRecaptchaScriptTagToMainHead(form);
}

const handleFlagSoundModal = () => {
    handleGenericModalWithForm(flagSoundButton.dataset.modalContentUrl, initSoundFlagForm, undefined, (req) => {showToast('Sound flagged successfully!')}, undefined);  
}

if (flagSoundModalParamValue) {
    handleFlagSoundModal();
}
flagSoundButton.addEventListener('click', (evt) => {
    handleFlagSoundModal();
})
