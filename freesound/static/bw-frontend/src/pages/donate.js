import { showToast } from '../components/toast';
import serialize from '../utils/formSerializer';

const formElement = document.getElementById('donation_form');
const formErrorlistElement = document.getElementsByClassName('errorlist')[0];
const donationButtonCreditCardElement = document.getElementById(
  'donation_button_credit_card'
);
const donationButtonPaypalElement = document.getElementById(
  'donation_button_paypal'
);
const recurringCheckboxElement = document.getElementById('id_recurring');
const nameOptionRadioButtons = [...document.getElementsByName('donation_type')];
const nameOptionOtherInputElement = document.getElementById('id_name_option');

// Make "other" input appear or disappear accordingly
nameOptionRadioButtons.forEach(element => {
  element.addEventListener('change', () => {
    if (element.value === '2') {
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
  donationButtonCreditCardElement.disabled = !!recurringCheckboxElement.checked;
});

function handleErrors(errors) {
  Object.entries(errors).forEach(([key, values]) => {
    const liElement = document.createElement('li');
    liElement.innerText = key;
    const newList = document.createElement('ul');
    newList.classList.add('errorlist', 'v-spacing-3');
    values.forEach(error => {
      const newLi = document.createElement('li');
      newLi.innerText = error;
      newList.appendChild(newLi);
    });
    // if we can find the element with the key as id, we add the error message to it
    const elemError = document.getElementById(`id_${key}`);
    if (elemError) {
      // add an error message below the input field
      elemError.insertAdjacentElement('afterend', newList);
    } else {
      // otherwise, we add it to the general error list (e.g., when key is '__all__')
      formErrorlistElement.appendChild(liElement);
      formErrorlistElement.appendChild(newList);
    }
  });
}

// Add actions for donate credit card/paypal buttons
donationButtonPaypalElement.addEventListener('click', event => {
  event.preventDefault(); // Stop propagation of submit event
  const req = new XMLHttpRequest();
  req.open(formElement.method, formElement.action, true);
  req.setRequestHeader(
    'Content-Type',
    'application/x-www-form-urlencoded; charset=UTF-8'
  );
  const params = serialize(formElement);
  req.onload = () => {
    if (req.status >= 200 && req.status < 300) {
      const data = JSON.parse(req.responseText);
      if (data.errors != null) {
        handleErrors(data.errors);
      } else {
        const hiddenFormElement = document.createElement('form');
        hiddenFormElement.setAttribute('action', data.url);
        hiddenFormElement.setAttribute('method', 'POST');
        hiddenFormElement.style.display = 'none';

        for (const [name, value] of Object.entries(data.params)) {
          const inputElement = document.createElement('input');
          inputElement.setAttribute('type', 'hidden');
          inputElement.setAttribute('name', name);
          inputElement.setAttribute('value', value);
          hiddenFormElement.appendChild(inputElement);
        }
        document.body.appendChild(hiddenFormElement);
        hiddenFormElement.submit();
      }
    }
  };
  req.onerror = () => {
    // Unexpected errors happened while processing request: show error in toast
    showToast(
      'Some errors occurred while processing the form. Please try again later.'
    );
  };
  req.send(params); // Send request
});

donationButtonCreditCardElement.addEventListener('click', event => {
  event.preventDefault(); // Stop propagation of submit event

  // The line below calls the Stripe object which is included in the template by loading external Stripe js api file
  var stripe = Stripe(donationButtonCreditCardElement.dataset.stripeKey);
  const req = new XMLHttpRequest();
  req.open(
    formElement.method,
    donationButtonCreditCardElement.dataset.stripeUrl,
    true
  );
  req.setRequestHeader(
    'Content-Type',
    'application/x-www-form-urlencoded; charset=UTF-8'
  );
  const params = serialize(formElement);
  req.onload = () => {
    if (req.status >= 200 && req.status < 300) {
      const data = JSON.parse(req.responseText);
      if (data.errors != null) {
        handleErrors(data.errors);
      } else {
        const session = data.session_id;
        stripe
          .redirectToCheckout({
            sessionId: session,
          })
          .then(function (result) {
            formErrorlistElement.innerHTML = '';
            const liElement = document.createElement('li');
            liElement.innerText =
              'Error calling stripe API, please retry later.';
            formErrorlistElement.appendChild(liElement);
          });
      }
    }
  };
  req.onerror = () => {
    // Unexpected errors happened while processing request: how error in toast
    showToast(
      'Some errors occurred while processing the form. Please try again later.'
    );
  };
  req.send(params); // Send request
});
