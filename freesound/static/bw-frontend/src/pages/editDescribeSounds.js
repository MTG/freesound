const tagsInputFields = document.getElementsByClassName('tags-field');

const drawWrapperContents = (inputWrapperElement, inputElement) => {
    const currentTags = inputWrapperElement.dataset.currentTags;

    const existingTagElements = inputWrapperElement.getElementsByTagName('span');
    [...existingTagElements].forEach(element => {element.remove()});

    currentTags.split(' ').forEach(tagToRender => {
        const tagElement = document.createElement('span');
        tagElement.innerText = tagToRender;
        tagElement.classList = 'no-hover btn-inverse text-black font-weight-normal border-grey-light text-center no-border-radius padding-1 no-text-wrap h-spacing-1 no-letter-spacing tag-container v-spacing-1';
        tagElement.style = 'background-color: white;';
        inputWrapperElement.insertBefore(tagElement, inputElement);
    });    
}

const keyCodeValidForTag = evt => {
    return ((evt.keyCode > 47 && evt.keyCode < 58)   || // number keys
    (evt.keyCode > 64 && evt.keyCode < 91)   || // letter keys
    (evt.keyCode > 95 && evt.keyCode < 112)  || // numpad keys
    (evt.keyCode == 189));   // -
};


tagsInputFields.forEach(tagsFieldElement => {
    const inputElement = tagsFieldElement.getElementsByClassName('tags-input')[0];
    const inputWrapperElement = tagsFieldElement.getElementsByClassName('tags-input-wrapper')[0];
    drawWrapperContents(inputWrapperElement, inputElement);
    inputElement.addEventListener('keypress', evt => {
        if ((evt.keyCode === 32) || (evt.keyCode === 13)){
            inputWrapperElement.dataset.currentTags += ' ' + inputElement.value;
            inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(/\s+/g, ' ').trim();  // Remove extra white spaces
            inputElement.value = '';
            drawWrapperContents(inputWrapperElement, inputElement);
            evt.preventDefault();
        } else {
            let res = inputElement.value.replace(/a-z/g, '');
            inputElement.value = res;
        }         
    });
    inputElement.addEventListener('input', evt => {
        console.log(inputElement.value)
        inputElement.value = inputElement.value.replace(/^a-zA-Z0-9 ]/g, '');
        console.log(inputElement.value.replace(/^a-zA-Z0-9 ]/g, ''), 'fixed')
        inputWrapperElement.dataset.currentTags += ' ' + inputElement.value;
        inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(/^a-zA-Z0-9 ]/g, ''); // Remove special characters
        inputWrapperElement.dataset.currentTags = inputWrapperElement.dataset.currentTags.replace(/\s+/g, ' ').trim();  // Remove extra white spaces
        inputElement.value = '';
        drawWrapperContents(inputWrapperElement, inputElement);
        
    });
    inputElement.addEventListener('focusin', evt => {
        inputWrapperElement.classList.add('tags-input-wrapper-focused');
    });
    inputElement.addEventListener('focusout', evt => {
        inputWrapperElement.classList.remove('tags-input-wrapper-focused');
    });
});