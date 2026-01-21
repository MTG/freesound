import { wrapInDiv } from '../utils/wrap';
import debounce from 'lodash.debounce';

const checkboxSelectAllElement = document.getElementById('selectAll');
const messageCheckboxes = document.getElementsByClassName('message-checkbox');
const actionsMenu = document.getElementsByClassName('actions-menu')[0];
const messageActionButtons = document.getElementsByClassName('message-action');
const LastMessageElement = document.getElementById('message-last');
const usernameToFormField = document.getElementById('username-to-field');

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
  const formElement = document.getElementById('message-action-form');
  document.getElementById('message_ids').value = messageIDs.join(',');
  document.getElementById('action_choice').value = actionType;
  formElement.submit();
};

// Bind actions message list actions

if (checkboxSelectAllElement !== null) {
  checkboxSelectAllElement.addEventListener('change', handleAllCheckboxes);
}

messageCheckboxes.forEach(checkbox =>
  checkbox.addEventListener('change', () => handleMessageCheckboxes(checkbox))
);

if (actionsMenu !== undefined) {
  actionsMenu
    .getElementsByClassName('bw-nav__action')
    .forEach(actionElement =>
      actionElement.addEventListener('click', () =>
        applyActionToMessages(
          actionElement.dataset.actionValue,
          getMessageIDsOfCheckedMessages()
        )
      )
    );
}

messageActionButtons.forEach(actionElement =>
  actionElement.addEventListener('click', () =>
    applyActionToMessages(actionElement.dataset.actionValue, [
      actionElement.parentNode.dataset.messageId,
    ])
  )
);

// Username check that username is valid
const usernameWarningElementId = 'dynamicUsernameInvalidWarning';

const returnUsernameWarningElement = () => {
  const xpath = "//li[contains(text(),'this username does not exist')]";
  return document.evaluate(
    xpath,
    document,
    null,
    XPathResult.FIRST_ORDERED_NODE_TYPE,
    null
  ).singleNodeValue;
};

const notifyUsernameInvalidWarning = () => {
  // Add dynamic warning to tell users the username is not valid
  if (
    document.getElementById(usernameWarningElementId) === null &&
    returnUsernameWarningElement() === null
  ) {
    const ulElement = document.createElement('ul');
    ulElement.id = usernameWarningElementId;
    ulElement.classList.add('errorlist');
    const liElement = document.createElement('li');
    liElement.innerText = 'We are sorry, but this username does not exist...';
    ulElement.appendChild(liElement);
    usernameToFormField.parentNode.parentNode.insertBefore(
      ulElement,
      usernameToFormField.parentNode
    );
  }
  // Add class to show username in red
  usernameToFormField.classList.add('username-not-found');
};

const removeUsernameInvalidWarning = () => {
  // If we added dynamic warning element, remove it
  if (document.getElementById(usernameWarningElementId) !== null) {
    document.getElementById(usernameWarningElementId).remove();
  }
  // Also if there was an error message from form validation in the server, remove it
  var matchingElement = returnUsernameWarningElement();
  if (matchingElement !== null) {
    matchingElement.remove();
  }

  // Remove username not found class
  usernameToFormField.classList.remove('username-not-found');
};

const checkUsername = async () => {
  const checkUsernameUrl = usernameToFormField.dataset.checkUsernameUrl;
  let response = await fetch(
    `${checkUsernameUrl}?username=${usernameToFormField.value}`
  );
  let data = await response.json();
  if (data.result === true) {
    // Note that we invert the condition as endpoint returns true if username is NOT taken
    notifyUsernameInvalidWarning();
  } else {
    removeUsernameInvalidWarning();
  }
};

if (usernameToFormField !== null) {
  const debouncedCheckUsername = debounce(checkUsername, 200, {
    leading: false,
    trailing: true,
  });
  usernameToFormField.addEventListener('input', async evt =>
    debouncedCheckUsername()
  );
  usernameToFormField.addEventListener('focusin', async evt =>
    debouncedCheckUsername()
  );
  usernameToFormField.addEventListener('focusout', async evt =>
    debouncedCheckUsername()
  );
}

// Username autocomplete functionality

import { addTypeAheadFeatures } from '../components/typeahead';

const fetchSuggestions = async inputElement => {
  const response = await fetch(
    inputElement.dataset.typeaheadSuggestionsUrl + '?q=' + inputElement.value
  );
  const returnedData = await response.json();
  const suggestions = [];
  returnedData.forEach(username => {
    suggestions.push({
      label: '<div class="padding-1">' + username + '</div>',
      value: username,
    });
  });
  return suggestions;
};

const onSuggestionSelectedFromDropdown = (
  suggestion,
  suggestionsWrapper,
  inputElement
) => {
  suggestionsWrapper.classList.add('hidden');
  inputElement.value = suggestion.value;
};

if (usernameToFormField !== null) {
  wrapInDiv(usernameToFormField, 'typeahead-wrapper');
  addTypeAheadFeatures(
    usernameToFormField,
    fetchSuggestions,
    onSuggestionSelectedFromDropdown,
    usernameToFormField.parentNode
  );
}
