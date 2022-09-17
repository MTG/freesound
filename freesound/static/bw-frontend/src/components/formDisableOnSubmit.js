// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

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

// @license-end
