const collapsableToggles = document.getElementsByClassName('collapsable-text');

const toggleCollapse = (toggleElement) => {
  const collapsableContainer = document.getElementById(toggleElement.dataset.target);
  collapsableContainer.classList.toggle('collapsable-block-close');
  const showText = toggleElement.dataset.showText;
  const hideText = toggleElement.dataset.hideText;
  toggleElement.textContent = collapsableContainer.classList.contains('collapsable-block-close')
    ? showText
    : hideText;
}

const handleCollapsable = (e) => {
  toggleCollapse(e.target);
};

collapsableToggles.forEach(element => {
  if (element.dataset.hideFromStart !== undefined){
    toggleCollapse(element);
  } else {
    element.textContent = element.dataset.hideText;
  }
  element.addEventListener('click', handleCollapsable);
});


