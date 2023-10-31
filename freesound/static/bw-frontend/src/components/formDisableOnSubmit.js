const bindDisableOnSubmitForms = () => {
    const formElementsWithDisableOnSubmit = document.getElementsByClassName("disable-on-submit");
    formElementsWithDisableOnSubmit.forEach(formElement => {
        
        if (formElement.dataset.alreadyBinded !== undefined){ return; }
        formElement.dataset.alreadyBinded = true;

        formElement.onsubmit = evt => {
            var buttonElements = formElement.getElementsByTagName('button');
            buttonElements.forEach(element => {
                element.disabled = true;
                if (element.name !== undefined && element == evt.submitter){
                    // If the button clicked to submit the form had an assigned name, we create an extra hidden input element with that 
                    // same name so it is included in the POST data. Otherwise the name would be excluded because the button is disabled
                    const hiddenInputElement = document.createElement('input');
                    hiddenInputElement.type = "hidden";
                    hiddenInputElement.name = element.name;
                    formElement.appendChild(hiddenInputElement);
                }
            });
            var inputTypeSubmitElements = formElement.querySelectorAll('input[type="submit"]');
            inputTypeSubmitElements.forEach(element => {
                element.disabled = true;
            });
            return true;
        };
    });

}

bindDisableOnSubmitForms();

export {bindDisableOnSubmitForms};