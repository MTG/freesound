import {makePostRequest} from "../utils/postRequest";
import {showToast} from "../components/toast";
import { addTypeAheadFeatures } from '../components/typeahead'
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
const checkUsernameUrl = usernameToFormField.dataset.checkUsernameUrl

const fetchSuggestions = async query => {
  let response = await fetch(`${usernamesPreviouslyContactedUrl}`)
  let data = await response.json()
  const suggestions = data.suggestions
  return suggestions
}

addTypeAheadFeatures(usernameToFormField, fetchSuggestions)


// Username check that username is valid

const checkUsername = async query => {
  let response = await fetch(`${checkUsernameUrl}?username=${usernameToFormField.value}`)
  let data = await response.json()
  if (data.result === false){
    usernameToFormField.classList.add('username-not-found')
  } else {
    usernameToFormField.classList.remove('username-not-found')
  }
}
const debouncedCheckusername = debounce(checkUsername, 200)
usernameToFormField.addEventListener('input', async evt => debouncedCheckusername())
