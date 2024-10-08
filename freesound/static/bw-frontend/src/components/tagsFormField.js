import { createIconElement } from '../utils/icons'
import { getJSONFromPostRequestWithFetch } from "../utils/postRequest";
import { addTypeAheadFeatures } from '../components/typeahead'
import { showToast } from './toast';

const fetchTagSuggestions = async inputElement => {
    const inputWrapperElement = inputElement.parentNode;
    let allTags = '';
    if (inputWrapperElement.dataset.currentTags !== ''){
        allTags = inputWrapperElement.dataset.currentTags + ' ' + inputElement.value;
    } else {
        allTags = inputElement.value;
    }
    const data = await getJSONFromPostRequestWithFetch(inputElement.dataset.typeaheadSuggestionsUrl, {'input_tags': allTags});
    const sugggestions = [];
    data[0].forEach(tag => {
        sugggestions.push({'label': '<div class="padding-1">' + tag + '</div>', 'value': tag})
    });
    return  sugggestions
}

const onSuggestionSelectedFromDropdown = (suggestion, suggestionsWrapper, inputElement) => {
    if (inputElement.focusoutTimeout !== undefined){ clearTimeout(inputElement.focusoutTimeout); inputElement.focusoutTimeout = undefined; }
    inputElement.value = '';
    updateTags(inputElement, suggestion.value);
    if (document.activeElement == inputElement){
        inputElement.dispatchEvent(new Event('input', {bubbles:true}));  // Dispatch "input" event to re-trigger tag recommendatiomn
    } else {
        inputElement.focus(); // Re-focus the input element (this will also re-trigger tag recommendation)
    }
}
  
const drawWrapperContents = (inputWrapperElement, inputElement, tagsHiddenInput) => {
    const currentTags = inputWrapperElement.dataset.currentTags;

    const existingTagElements = inputWrapperElement.getElementsByTagName('span');
    [...existingTagElements].forEach(element => {element.remove()});

    let someTagsRendered = false;
    currentTags.split(' ').forEach((tagToRender, index) => {
        if (tagToRender !== ''){
            someTagsRendered = true;
            const tagElement = document.createElement('span');
            tagElement.innerText = tagToRender;
            tagElement.classList = 'bg-white text-black border-grey-light text-center padding-1 no-text-wrap no-letter-spacing h-spacing-1 v-spacing-1';
            tagElement.dataset.index = index;
            const closeIconNode = createIconElement('bw-icon-close');
            closeIconNode.addEventListener('click', evt => {
                const userWasEditingTags = inputElement.focusoutTimeout != undefined;  // This is because if user removed a tag while havin input element focused, it will just be loosing focus and the timeout will be running
                if (inputElement.focusoutTimeout !== undefined){ clearTimeout(inputElement.focusoutTimeout); inputElement.focusoutTimeout = undefined;}
                const currentTagsArray = inputWrapperElement.dataset.currentTags.split(' ');
                currentTagsArray.splice(index, 1)
                inputWrapperElement.dataset.currentTags = currentTagsArray.join(' ');
                updateTags(inputElement, '');
                if (userWasEditingTags){
                    inputElement.focus();
                } else {
                    inputElement.value = '';
                }                
            });
            tagElement.appendChild(closeIconNode);
            inputWrapperElement.insertBefore(tagElement, inputElement);
        }
    });

    if (someTagsRendered){
        // Add action buttons
        const buttonsWrapper = document.createElement('div');
        buttonsWrapper.style="position:absolute;right:10px;top:-33px;z-index:1;";
        inputWrapperElement.appendChild(buttonsWrapper);

        const copyTagsButton = document.createElement('a');
        copyTagsButton.title = "Copy the tags from this sound"
        copyTagsButton.ariaLabel = "Copy the tags from this sound"
        copyTagsButton.innerHTML = '<span class="bw-icon bw-icon-copy"></span>';
        copyTagsButton.className = 'bw-link--grey no-hover cursor-pointer'
        copyTagsButton.addEventListener('click', evt => {
            evt.preventDefault();
            navigator.clipboard.writeText(tagsHiddenInput.value);
            showToast(`Tags "${tagsHiddenInput.value}" copied to clipboard`);
        })
        buttonsWrapper.appendChild(copyTagsButton);

        const clearTagsButton = document.createElement('a');
        clearTagsButton.title = "Clear tags"
        clearTagsButton.ariaLabel = "Clear tags"
        clearTagsButton.innerHTML = '<span class="bw-icon bw-icon-close"></span>';
        clearTagsButton.className = 'bw-link--grey no-hover cursor-pointer h-spacing-left-1'
        clearTagsButton.style = 'font-size: 10px;'
        clearTagsButton.addEventListener('click', evt => {
            evt.preventDefault();
            inputWrapperElement.dataset.currentTags = '';
            updateTags(inputElement, '');
        })
        buttonsWrapper.appendChild(clearTagsButton);
    }    
}

const allowedTagCharactersTestRegex = new RegExp('^[a-zA-Z0-9-]$');
const notAlphanumericDashOrSpaceRegex = new RegExp('[^a-zA-Z0-9- ]', 'g');
const multiDashesRegex = new RegExp('-+', 'g');

const updateTags = (inputElement, newTagsStr)  => {
    const inputWrapperElement = inputElement.parentNode;
    const tagsHiddenInput = inputElement.parentNode.parentNode.parentNode.querySelectorAll('input[name$="tags"]')[0]
    inputWrapperElement.dataset.currentTags += ' ' + newTagsStr;
    inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(notAlphanumericDashOrSpaceRegex, '');  // Remove non-alphanumeric, dash or space
    inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(multiDashesRegex, '-');  // Remove multi-dashes
    inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.split(' ').filter(item => !(item === '-')).join(' ');  // Remove 1 character tags which are a dash
    inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(/\s+/g, ' ').trim();  // Remove extra white spaces
    tagsHiddenInput.value = inputWrapperElement.dataset.currentTags;
    drawWrapperContents(inputWrapperElement, inputElement, tagsHiddenInput);
}

const prepareTagsFormFields = (container) => {
    const tagsInputFields = container.getElementsByClassName('tags-field');
    tagsInputFields.forEach(tagsFieldElement => {
        const tagsHiddenInput = tagsFieldElement.querySelectorAll('input[name$="tags"]')[0];
        const inputElement = tagsFieldElement.getElementsByClassName('tags-input')[0];
        inputElement.focusoutTimeout = undefined;
        const inputWrapperElement = tagsFieldElement.getElementsByClassName('tags-input-wrapper')[0];
        if (inputWrapperElement.dataset.currentTags === undefined){
            inputWrapperElement.dataset.currentTags = '';
        }
        updateTags(inputElement, tagsHiddenInput.value);
        
        addTypeAheadFeatures(inputElement, fetchTagSuggestions, onSuggestionSelectedFromDropdown);

        const tagSeparatorKeys = ["Enter", " ", ","];

        inputElement.addEventListener('keypress', evt => {
            if (tagSeparatorKeys.includes(evt.key)){
                evt.preventDefault(); // Do not submit form is key is enter, and also do not add " " or "," chars to the input field
                const newTagsStr = inputElement.value;
                inputElement.value = '';
                updateTags(inputElement, newTagsStr);
            } else if (!allowedTagCharactersTestRegex.test(evt.key)){
                evt.preventDefault();  // Do not allow characters which are not accepted in tags input
            }
        })

        inputElement.addEventListener('keydown', evt => {
            if ((evt.key == "Backspace") && (inputElement.value.length == 0)){
                // Backspace can only be detected in "keydown" events
                const currentTagsArray = inputWrapperElement.dataset.currentTags.split(' ');
                const lastIntroducedTag = inputWrapperElement.dataset.currentTags.split(' ')[currentTagsArray.length - 1];
                inputWrapperElement.dataset.currentTags = currentTagsArray.slice(0,currentTagsArray.length - 1).join(" ");
                const lastIntroducedTagElement = inputElement.previousSibling;
                if (lastIntroducedTagElement != undefined){
                    lastIntroducedTagElement.remove();
                }
                inputElement.value = lastIntroducedTag.substring(0, lastIntroducedTag.length - 1);
            }
        })
        
        inputElement.addEventListener('paste', evt => {
            let pasteText = (evt.clipboardData || window.clipboardData).getData('text');
            pasteText = pasteText.replace(/\n/g, ' '); // Replace newlines with spaces, can happen if coppying from other tag fields
            updateTags(inputElement, inputElement.value + pasteText);
            evt.preventDefault();   
        });

        inputElement.addEventListener('focusin', evt => {
            inputWrapperElement.classList.add('tags-input-wrapper-focused');
        });

        inputElement.addEventListener('focusout', evt => {
            inputWrapperElement.classList.remove('tags-input-wrapper-focused');
            inputElement.focusoutTimeout = setTimeout(() => {
                inputElement.focusoutTimeout = undefined;  // Set variable to undefined so I can check if timer is running from outside
                // Use timeout here to prevent the event of removing one tag to be cancelled by calling
                // updateTags because clicking on the element removes focus from tags-input.
                // Also we want to delay that action because when a focusout event is triggered because of
                // user clicking on a tag suggestion (or when removing an existing tag), we don't want the effects 
                // of the focusout event to be applied
                const newTagsStr = inputElement.value;
                inputElement.value = '';
                updateTags(inputElement, newTagsStr);
            }, 200);
        });
    });
}

export {prepareTagsFormFields}
