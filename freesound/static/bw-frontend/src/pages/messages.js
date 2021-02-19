const CheckboxGetAllElement = document.getElementById('selectAll');
const messageCheckboxes = document.getElementsByClassName('message-checkbox');
const checkboxesActions = document.getElementsByClassName('checked-action');
const LastMessageElement = document.getElementById('message-last');

if (LastMessageElement) {
  LastMessageElement.focus();
}

const handleAllCheckboxes = () => {
  const allCheckboxes = document.getElementsByClassName('message-checkbox');

  allCheckboxes.forEach(checkboxElement => {
    checkboxElement.checked = CheckboxGetAllElement.checked;
    handleActions(CheckboxGetAllElement.checked);
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
  checkboxesActions.forEach(
    checkboxesActions => (checkboxesActions.style.display = show ? 'flex' : 'none')
  );
};

messageCheckboxes.forEach(checkbox =>
  checkbox.addEventListener('change', () => handleMessageCheckboxes(checkbox))
);

CheckboxGetAllElement.addEventListener('change', handleAllCheckboxes);
