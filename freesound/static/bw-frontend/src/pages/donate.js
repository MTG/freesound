// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import {handleDismissModal, handleModal} from "../components/modal";
import {showToast} from "../components/toast";
import serialize from "../utils/formSerializer";

const formElement = document.getElementById('donation_form');
const formErrorlistElement = document.getElementsByClassName('errorlist')[0];
const donationButtonCreditCardElement = document.getElementById('donation_button_credit_card');
const donationButtonPaypalElement = document.getElementById('donation_button_paypal');
const recurringCheckboxElement = document.getElementById('id_recurring');
const nameOptionRadioButtons = document.getElementsByName('donation_type');
const nameOptionOtherInputElement = document.getElementById('id_name_option');

// Make "other" input appear or disappear accordingly
nameOptionRadioButtons.forEach(element => {
    element.addEventListener('change', () => {
        if (element.value === "2"){
            // Other option has been selected, make the input text visible
            nameOptionOtherInputElement.classList.remove('display-none');
        } else {
            // Option other is not selected, make the input text invisible
            nameOptionOtherInputElement.classList.add('display-none');
        }
    });
});

// Disable credit card button if recurring option is checked
recurringCheckboxElement.addEventListener('change', () => {
    if (recurringCheckboxElement.checked) {
        donationButtonCreditCardElement.disabled = true;
    } else {
        donationButtonCreditCardElement.disabled = false;
    }

});

// Add actions for donate credit card/paypal buttons
donationButtonPaypalElement.addEventListener('click', (event) => {
    event.preventDefault();  // Stop propagation of submit event
    const req = new XMLHttpRequest();
    req.open(formElement.method, formElement.action, true);
    req.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
    const params = serialize(formElement);
    req.onload = () => {
        if (req.status >= 200 && req.status < 300) {
            const data = JSON.parse(req.responseText);
            if (data.errors != null) {
                formErrorlistElement.innerHTML = '';
                data.errors['__all__'].forEach(error => {
                    const liElement = document.createElement("li");
                    liElement.innerText = error;
                    formErrorlistElement.appendChild(liElement);
                });
            } else {
                const hiddenFormElement = document.createElement("form");
                hiddenFormElement.setAttribute("action", data.url);
                hiddenFormElement.setAttribute("method", "POST");
                hiddenFormElement.style.display = 'none';

                for (const [name, value] of Object.entries(data.params)) {
                  const inputElement = document.createElement("input");
                    inputElement.setAttribute("type", "hidden");
                    inputElement.setAttribute("name", name);
                    inputElement.setAttribute("value", value);
                    hiddenFormElement.appendChild(inputElement);
                }
                document.body.appendChild(hiddenFormElement);
                hiddenFormElement.submit();
            }
        }
    }
    req.onerror = () => {
        // Unexpected errors happened while processing request: how error in toast
        showToast('Some errors occurred while processing the form. Please try again later.')
    };
    req.send(params); // Send request
});

donationButtonCreditCardElement.addEventListener('click', (event) => {
    event.preventDefault();  // Stop propagation of submit event

    // The line below calls the Stripe object which is included in the template by loading external Stripe js api file
    var stripe = Stripe(donationButtonCreditCardElement.dataset.stripeKey);
    const req = new XMLHttpRequest();
    req.open(formElement.method, donationButtonCreditCardElement.dataset.stripeUrl, true);
    req.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
    const params = serialize(formElement);
    req.onload = () => {
        if (req.status >= 200 && req.status < 300) {
            const data = JSON.parse(req.responseText);
            if (data.errors != null) {
                formErrorlistElement.innerHTML = '';
                data.errors['__all__'].forEach(error => {
                    const liElement = document.createElement("li");
                    liElement.innerText = error;
                    formErrorlistElement.appendChild(liElement);
                });
            } else {
                const session = data.session_id;
                stripe.redirectToCheckout({
                    sessionId: session
                }).then(function (result) {
                    formErrorlistElement.innerHTML = '';
                    const liElement = document.createElement("li");
                    liElement.innerText = "Error calling stripe API, please retry later.";
                    formErrorlistElement.appendChild(liElement);
                });
            }
        }
    }
    req.onerror = () => {
        // Unexpected errors happened while processing request: how error in toast
        showToast('Some errors occurred while processing the form. Please try again later.')
    };
    req.send(params); // Send request
});

// @license-end
