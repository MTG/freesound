const CheckboxGetAllElement = document.getElementById('selectAll');

const handleAllCheckboxes = () => {
  const allCheckboxes = document.getElementsByClassName('message-checkbox');

  allCheckboxes.forEach(
    checkboxElement => (checkboxElement.checked = CheckboxGetAllElement.checked)
  );
};

CheckboxGetAllElement.addEventListener('change', handleAllCheckboxes);
