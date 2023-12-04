const formFieldShouldAllowEnterEvents = (element) => {
    if (element.tagName == "TEXTAREA"){
        return true;
    } else if (element.classList.contains('tags-input')) {
        return true;
    }
    return false;
}

const bindDoNotSubmitOnEnterForms = (container) => {
    var formElements = container.getElementsByClassName("do-not-submit-on-enter");
    formElements.forEach(formElement => {
        formElement.onkeydown = evt => {
            if (evt.key == "Enter" && !formFieldShouldAllowEnterEvents(evt.target)) {
                evt.preventDefault();
            }
        };
    });    
}

export {bindDoNotSubmitOnEnterForms};
