document.addEventListener("DOMContentLoaded", function(){
    var formElementsWithDisableOnSubmit = document.getElementsByClassName("disable-on-submit");
    for(var i=0; i<formElementsWithDisableOnSubmit.length; i++){
        var formElement = formElementsWithDisableOnSubmit[i];
        formElement.onsubmit = function(){
            var buttonElements = formElement.getElementsByTagName('button');
            for (var j=0; j<buttonElements.length; j++){
                buttonElements[j].disabled = true;
            }
            var inputTypeSubmit = formElement.querySelectorAll('input[type="submit"]');
            for (var j=0; j<inputTypeSubmit.length; j++){
                inputTypeSubmit[j].disabled = true;
            }
            return true;
        };
    }
});
