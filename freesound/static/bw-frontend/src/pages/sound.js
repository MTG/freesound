import './page-polyfills';
import {showToast} from '../components/toast';
import {playAtTime} from '../components/player/utils';
import {openSimilarSoundsModal} from "../components/similarSoundsModal";
import {handleGenericModal, handleDismissModal} from '../components/modal';
import {createSelect} from "../components/select";
import {addRecaptchaScriptTagToMainHead} from '../utils/recaptchaDynamicReload'
import serialize from '../utils/formSerializer'

const toggleEmbedCodeElement = document.getElementById('toggle-embed-code');
const toggleShareLinkElement = document.getElementById('toggle-share-link');
const embedLinksElement = document.getElementById('embed-links');
const embedCodeElement = document.getElementById('embed-code');
const smallEmbedImageElement = document.getElementById('small-embed-image');
const mediumEmbedImageElement = document.getElementById('medium-embed-image');
const largeEmbedImageElement = document.getElementById('large-embed-image');
const shareLinkElement = document.getElementById('share-link');
const urlParams = new URLSearchParams(window.location.search);

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

// Open similar sounds modal if activation parameter is passed
const similarSoundsButtons = [...document.querySelectorAll('[data-toggle^="similar-sounds-modal"]')];
if (similarSoundsButtons.length > 0){
    const similarSoundsModalActivationParam = similarSoundsButtons[0].dataset.modalActivationParam;
    const similarSoundsModalParamValue = urlParams.get(similarSoundsModalActivationParam);
    if (similarSoundsModalParamValue) {
        openSimilarSoundsModal(similarSoundsButtons[0].dataset.modalContentUrl, similarSoundsModalActivationParam);
    }
}


// Open flag sound modal if activation parameter is passed
const flagSoundButton = [...document.querySelectorAll('[data-toggle^="flag-sound-modal"]')][0];
const flagSoundModalActivationParam = flagSoundButton.dataset.modalActivationParam;
const flagSoundModalParamValue = urlParams.get(flagSoundModalActivationParam);

const initSoundFlagForm = () => {
    // Modify the form structure to add a "Reason type:" label inline with the select dropdown
    const modalElement = document.getElementById(`flagSoundModal`);;
    const selectElement = modalElement.getElementsByTagName('select')[0];
    const wrapper = document.createElement('div');
    selectElement.parentNode.insertBefore(wrapper, selectElement);
    const label = document.createElement('div');
    label.innerHTML = "Reason type:"
    label.style = 'display:inline-block;';
    label.classList.add('text-grey');
    wrapper.appendChild(label)
    wrapper.appendChild(selectElement)

    // Init select and recaptcha fields
    const form = modalElement.getElementsByTagName('form')[0];
    createSelect();
    addRecaptchaScriptTagToMainHead(form);

    // Set custom submit function so we can show errors properly, etc
    form.onsubmit = (evt) => {
        customFlagSoundFormSubmit(evt);
        evt.preventDefault();
    }
}

const handleFlagSoundModal = () => {
    handleGenericModal(flagSoundButton.dataset.modalContentUrl, () => {
        initSoundFlagForm();
    });
}

const customFlagSoundFormSubmit = (event) => {

    const modalElement = document.getElementById("flagSoundModal");
    const form = modalElement.getElementsByTagName('form')[0];
    const params = serialize(form);
    
    // Create new Ajax request to submit flag form contents
    const req = new XMLHttpRequest();
    req.open('POST', form.action, true);
    req.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
    req.onload = () => {
        if (req.status >= 200 && req.status < 300) {
            if (req.getResponseHeader('content-type') === 'application/json'){
                // If response is of type JSON, that means flagging was successful, show toast and close modal
                handleDismissModal('flagSoundModal');
                showToast('Sound flagged successfully!')
            }  else {
                // There were errors in the flag form. In that case the response are the HTML elements of the
                // form (including error warnings) and we should replace current modal HTML with this one (and 
                // re-init all needed javascript)
                const genericModalWrapper = modalElement.parentNode;
                genericModalWrapper.innerHTML = req.responseText;
                const modalContainerId = genericModalWrapper.getElementsByClassName('modal')[0].id;
                const modalContainer = document.getElementById(modalContainerId);
                modalContainer.classList.add('show');
                modalContainer.style.display = 'block';
                const form = modalContainer.getElementsByTagName('form')[0];
                initSoundFlagForm();
                const modalDismiss = genericModalWrapper.querySelectorAll('[data-dismiss="modal"]');
                modalDismiss.forEach(dismiss => {
                    dismiss.addEventListener('click', () => {
                        handleDismissModal('flagSoundModal');});
                });
            }
        }
    };
    req.onerror = () => {
        // Unexpected errors happened while processing request: close modal and show error in toast
        handleDismissModal('flagSoundModal');
        showToast('Some errors occurred while processing the form. Please try again later.')
    };

    // Send the form
    req.send(params);

    // Return false so default submission does not happen
    return false;
};


if (flagSoundModalParamValue) {
    handleFlagSoundModal();
}
flagSoundButton.addEventListener('click', (evt) => {
    handleFlagSoundModal();
})
