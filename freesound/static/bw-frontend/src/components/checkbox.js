const addVisibleCheckbox = (checkboxEl) => {
  const parent = checkboxEl.parentNode
  const actualCheckboxIndex = [...parent.children].findIndex(el => [...el.classList].includes('bw-checkbox'))
  const insertBeforeElement = [...parent.children][actualCheckboxIndex + 1]
  const visibleCheckboxContainer = document.createElement('span')
  visibleCheckboxContainer.className = 'bw-checkbox-container'
  parent.insertBefore(visibleCheckboxContainer, insertBeforeElement)
  const checkboxIcon = document.createElement('span')
  checkboxIcon.className = 'bw-icon-checkbox'
  visibleCheckboxContainer.append(checkboxIcon)
}

const addCheckboxVisibleElements = () => {
  const checkboxes = [...document.getElementsByClassName('bw-checkbox')];
  checkboxes.forEach(addVisibleCheckbox)
};

addCheckboxVisibleElements();

export default addCheckboxVisibleElements;