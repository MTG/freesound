const bindDoNotSubmitOnEnterForms = (container) => {
    var formElements = container.getElementsByClassName("do-not-submit-on-enter");
    formElements.forEach(formElement => {
        formElement.onkeydown = evt => {
            if (evt.key == "Enter") {
                evt.preventDefault();
            }
        };
    });    
}

export {bindDoNotSubmitOnEnterForms};
