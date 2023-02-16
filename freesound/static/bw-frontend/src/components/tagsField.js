import { createIconElement } from '../utils/icons'

const tagsInputFields = document.getElementsByClassName('tags-field');

const drawWrapperContents = (inputWrapperElement, inputElement, tagsHiddenInput) => {
    const currentTags = inputWrapperElement.dataset.currentTags;

    const existingTagElements = inputWrapperElement.getElementsByTagName('span');
    [...existingTagElements].forEach(element => {element.remove()});

    currentTags.split(' ').forEach((tagToRender, index) => {
        if (tagToRender !== ''){
            const tagElement = document.createElement('span');
            tagElement.innerText = tagToRender;
            tagElement.classList = 'bg-white text-black border-grey-light text-center padding-1 no-text-wrap no-letter-spacing h-spacing-1 v-spacing-1';
            tagElement.dataset.index = index;
            const closeIconNode = createIconElement('bw-icon-close');
            closeIconNode.addEventListener('click', evt => {
                const currentTagsArray = inputWrapperElement.dataset.currentTags.split(' ');
                currentTagsArray.splice(index, 1)
                inputWrapperElement.dataset.currentTags = currentTagsArray.join(' ');
                updateTags(inputWrapperElement, inputElement, tagsHiddenInput, '');
            });
            tagElement.appendChild(closeIconNode);
            inputWrapperElement.insertBefore(tagElement, inputElement);
        }
    });    
}

const allowedTagCharactersTestRegex = new RegExp('^[a-zA-Z0-9-]$');
const notAlphanumericDashOrSpaceRegex = new RegExp('[^a-zA-Z0-9- ]', 'g');
const multiDashesRegex = new RegExp('-+', 'g');

const updateTags = (inputWrapperElement, inputElement, tagsHiddenInput, newTagsStr)  => {
    if (inputWrapperElement.dataset.currentTags === undefined){
        inputWrapperElement.dataset.currentTags = '';
    }
    inputWrapperElement.dataset.currentTags += ' ' + newTagsStr;
    inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(notAlphanumericDashOrSpaceRegex, '');  // Remove non-alphanumeric, dash or space
    inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(multiDashesRegex, '-');  // Remove multi-dashes
    inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.split(' ').filter(item => !(item === '-')).join(' ');  // Remove 1 character tags which are a dash
    inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(/\s+/g, ' ').trim();  // Remove extra white spaces
    tagsHiddenInput.value = inputWrapperElement.dataset.currentTags;
    drawWrapperContents(inputWrapperElement, inputElement, tagsHiddenInput);
}

tagsInputFields.forEach(tagsFieldElement => {
    const inputElement = tagsFieldElement.getElementsByClassName('tags-input')[0];
    const inputWrapperElement = tagsFieldElement.getElementsByClassName('tags-input-wrapper')[0];
    const tagsHiddenInput = tagsFieldElement.querySelectorAll('input[name$="tags"]')[0];
    updateTags(inputWrapperElement, inputElement, tagsHiddenInput, tagsHiddenInput.value);

    inputElement.addEventListener('keypress', evt => {
        if (evt.key == "Enter"){
            evt.preventDefault();  // Do not submit form
            const newTagsStr = inputElement.value;
            inputElement.value = '';
            updateTags(inputWrapperElement, inputElement, tagsHiddenInput, newTagsStr);
        } else if (evt.key == " "){
            const newTagsStr = inputElement.value;
            inputElement.value = '';
            updateTags(inputWrapperElement, inputElement, tagsHiddenInput, newTagsStr);
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
        updateTags(inputWrapperElement, inputElement, tagsHiddenInput, inputElement.value + pasteText);
        evt.preventDefault();   
    });

    inputElement.addEventListener('focusin', evt => {
        inputWrapperElement.classList.add('tags-input-wrapper-focused');
    });

    inputElement.addEventListener('focusout', evt => {
        inputWrapperElement.classList.remove('tags-input-wrapper-focused');
        const newTagsStr = inputElement.value;
        inputElement.value = '';
        setTimeout(() => {
            // Use timeout here to prevent the event of removing one tag to be cancelled by calling
            // updateTags because clicking on the element removes focus from tags-input
            updateTags(inputWrapperElement, inputElement, tagsHiddenInput, newTagsStr);
        }, 100);
    });
});