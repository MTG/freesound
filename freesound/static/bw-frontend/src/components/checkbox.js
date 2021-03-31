const addVisibleCheckbox = (checkboxEl) => {
  // Check if checkbox has a label element and re-order them
  // We need to do this because Django does not provide an easy way to order checkbox/labels differently than
  // the default
  const labelEl = checkboxEl.previousElementSibling;
  if ((labelEl) && (labelEl.tagName === 'LABEL')){
      const wrapperEl = document.createElement('div');
      checkboxEl.parentNode.insertBefore(wrapperEl, checkboxEl);
      wrapperEl.appendChild(checkboxEl);
      wrapperEl.appendChild(labelEl);
      labelEl.classList.add('input-checkbox-label-default');
  }

  // Create the visible version of checkbox element
  const parent = checkboxEl.parentNode
  const actualCheckboxIndex = [...parent.children].findIndex(el => [...el.classList].includes('bw-checkbox'))
  const insertBeforeElement = [...parent.children][actualCheckboxIndex + 1]

  let visibleElementAlreadyAdded = false;
  if ((insertBeforeElement !== undefined) && (insertBeforeElement.classList.contains('bw-checkbox-container'))) {
    visibleElementAlreadyAdded = true;
  }
  if (!visibleElementAlreadyAdded){
    // Only add the visible checkbox element if it has not yet been added before
    const visibleCheckboxContainer = document.createElement('span')
    visibleCheckboxContainer.className = 'bw-checkbox-container'
    parent.insertBefore(visibleCheckboxContainer, insertBeforeElement)
    const checkboxIcon = document.createElement('span')
    checkboxIcon.className = 'bw-icon-checkbox'
    visibleCheckboxContainer.append(checkboxIcon)
  }
};

const addCheckboxVisibleElements = () => {
  const checkboxes = [...document.getElementsByClassName('bw-checkbox')];
  checkboxes.forEach(addVisibleCheckbox)
};

addCheckboxVisibleElements();

export default addCheckboxVisibleElements;