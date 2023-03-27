var formElements = document.getElementsByClassName("do-not-submit-on-enter");
formElements.forEach(formElement => {
    formElement.onkeydown = evt => {
        if (evt.key == "Enter") {
            evt.preventDefault();
        }
    };
});    
