import { makePostRequest } from "../utils/postRequest";
import { showToast } from "../components/toast";
import { addAutocomplete } from '../components/autocomplete'
import debounce from 'lodash.debounce'


const checkboxSelectAllElement = document.getElementById('selectAll');
const messageCheckboxes = document.getElementsByClassName('message-checkbox');
const actionsMenu = document.getElementsByClassName('actions-menu')[0];
const messageActionButtons = document.getElementsByClassName('message-action');
const LastMessageElement = document.getElementById('message-last');
const messageInfoContainers = document.getElementsByClassName('bw-message__info');
const usernameToFormField = document.getElementById('usernames-autocomplete')

if (LastMessageElement) {
  LastMessageElement.focus();
}

const handleAllCheckboxes = () => {
  
  const allCheckboxes = document.getElementsByClassName('message-checkbox');

  allCheckboxes.forEach(checkboxElement => {
    checkboxElement.checked = checkboxSelectAllElement.checked;
    handleActions(checkboxSelectAllElement.checked);
  });
};

const handleMessageCheckboxes = () => {
  let isAnyCheckboxChecked = false;

  messageCheckboxes.forEach(checkbox => {
    if (checkbox.checked) {
      isAnyCheckboxChecked = true;
    }
  });

  handleActions(isAnyCheckboxChecked);
};

const handleActions = show => {
  actionsMenu.style.display = show ? 'inline' : 'none';
};

const getMessageIDsOfCheckedMessages = () => {
  let messageIDs = [];
  messageCheckboxes.forEach(checkbox => {
    if (checkbox.checked) {
      const messageID = checkbox.id.replace('message', '');
      messageIDs.push(messageID);
    }
  });
  return messageIDs;
};

const applyActionToMessages = (actionType, messageIDs) => {
  const applyActionUrl = actionsMenu.dataset.applyActionUrl;
  const nextUrl = actionsMenu.dataset.nextUrl;

  // Make a post request that will perform the action, the response will redirect accordingly
  let formData = {};
  formData.next = nextUrl;
  formData.choice = actionType;
  formData.ids = messageIDs.join(',');

  makePostRequest(applyActionUrl, formData, (responseText) => {
      // Post request returned successfully, reload the page
      document.location.reload();
  }, () => {
      showToast("An unexpected error occurred while performing the action");
  });
};


// Bind actions message list actions

if (checkboxSelectAllElement !== null){
  checkboxSelectAllElement.addEventListener('change', handleAllCheckboxes);
}

messageCheckboxes.forEach(checkbox =>
  checkbox.addEventListener('change', () => handleMessageCheckboxes(checkbox))
);

if (actionsMenu !== undefined){
  actionsMenu.getElementsByClassName('bw-nav__action').forEach(actionElement =>
    actionElement.addEventListener('click', () => applyActionToMessages(actionElement.dataset.actionValue, getMessageIDsOfCheckedMessages()))
  );
}

messageActionButtons.forEach(actionElement =>
  actionElement.addEventListener('click', () => applyActionToMessages(actionElement.dataset.actionValue, [actionElement.parentNode.dataset.messageId]))
);

messageInfoContainers.forEach(messageContainer =>
  messageContainer.addEventListener('click', () => window.location = messageContainer.dataset.linkUrl)
);

// Username lookup for new messages
const usernamesPreviouslyContactedUrl = usernameToFormField.dataset.autocompleteSuggestionsUrl

const setupAtocomplete = async () => {
  let response = await fetch(`${usernamesPreviouslyContactedUrl}`)
  let data = await response.json()
  addAutocomplete(document.getElementById('usernames-autocomplete'), data.usernames);
}

setupAtocomplete();

// Username check that username is valid
const checkUsernameUrl = usernameToFormField.dataset.checkUsernameUrl
const usernameWarningElementId = 'dynamicUsernameInvalidWarning';

const returnUsernameWarningElement = () => {
  const xpath = "//li[contains(text(),'this username does not exist')]";
  return document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
}

const notifyUsernameInvalidWarning = () => {
  // Add dynamic warning to tell users the username is not valid
  if (document.getElementById(usernameWarningElementId) === null && returnUsernameWarningElement() === null){
    const ulElement = document.createElement('ul');
    ulElement.id = usernameWarningElementId;
    ulElement.classList.add('errorlist');
    const liElement = document.createElement('li');
    liElement.innerText = 'We are sorry, but this username does not exist...'
    ulElement.appendChild(liElement);
    usernameToFormField.parentNode.parentNode.insertBefore(ulElement, usernameToFormField.parentNode);
  }
  // Add class to show username in red
  usernameToFormField.classList.add('username-not-found')
}

const removeUsernameInvalidWarning = () => {
  // If we added dynamic warning element, remove it
  if (document.getElementById(usernameWarningElementId) !== null){
    document.getElementById(usernameWarningElementId).remove();
  }
  // Also if there was an error message from form validation in the server, remove it
  var matchingElement = returnUsernameWarningElement();
  if (matchingElement !== null){
    matchingElement.remove();
  }

  // Remove username not found class
  usernameToFormField.classList.remove('username-not-found')
}

const checkUsername = async () => {
  let response = await fetch(`${checkUsernameUrl}?username=${usernameToFormField.value}`)
  let data = await response.json()
  if (data.result === true){ // Note that we invert the condition as endpoint returns true if username is NOT taken
    notifyUsernameInvalidWarning();
  } else {
    removeUsernameInvalidWarning();
  }
}

const debouncedCheckUsername = debounce(checkUsername, 200, {'leading': false, 'trailing': true})
usernameToFormField.addEventListener('input', async evt => debouncedCheckUsername())
usernameToFormField.addEventListener('focusin', async evt => debouncedCheckUsername())
usernameToFormField.addEventListener('focusout', async evt => debouncedCheckUsername())
