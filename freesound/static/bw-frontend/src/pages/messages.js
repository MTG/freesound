import {makePostRequest} from "../utils/postRequest";
import {handleDismissModal} from "../components/modal";
import {showToast} from "../components/toast";

const checkboxSelectAllElement = document.getElementById('selectAll');
const messageCheckboxes = document.getElementsByClassName('message-checkbox');
const actionsMenu = document.getElementsByClassName('actions-menu')[0];
const messageActionButtons = document.getElementsByClassName('message-action');
const LastMessageElement = document.getElementById('message-last');

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
  console.log(actionType, messageIDs);

  const applyActionUrl = actionsMenu.dataset.applyActionUrl;

  // Make a post request that will perform the action, the response will redirect accordingly
  let formData = {};
  formData.next = "/home/messages/";
  formData.choice = actionType;
  formData.ids = messageIDs.join(',');

  makePostRequest(applyActionUrl, formData, (responseText) => {
      // Post request returned successfully, reload the page
      document.location.reload();
  }, () => {
      showToast("An unexpected error occurred while performing the action");
  });
};


// Bind actions

messageCheckboxes.forEach(checkbox =>
  checkbox.addEventListener('change', () => handleMessageCheckboxes(checkbox))
);

checkboxSelectAllElement.addEventListener('change', handleAllCheckboxes);

actionsMenu.getElementsByClassName('bw-nav__action').forEach(actionElement =>
  actionElement.addEventListener('click', () => applyActionToMessages(actionElement.dataset.actionValue, getMessageIDsOfCheckedMessages()))
);

messageActionButtons.forEach(actionElement =>
  actionElement.addEventListener('click', () => applyActionToMessages(actionElement.dataset.actionValue, [actionElement.dataset.messageId]))
);