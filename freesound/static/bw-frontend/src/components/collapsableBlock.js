const collapsableToggles = document.getElementsByClassName('collapsable-toggle');

const toggleCollapse = (toggleElement) => {
  const collapsableContainer = document.getElementById(toggleElement.dataset.target);
  let closeClass =  'collapsable-block-close';
  if (toggleElement.dataset.maxHeightWhenClosed !== undefined) {
    closeClass =  'collapsable-block-close-gradient';
    if (collapsableContainer.classList.contains('collapsable-block-close-gradient')) {
      // If the block contains the closed gradient class, it means we will expand the collapsable block now so we 
      // unset the height that we manually set from the dataset property
      collapsableContainer.style.maxHeight = 'unset';
    } else {
      collapsableContainer.style.maxHeight = toggleElement.dataset.maxHeightWhenClosed + 'px';
    }
  }
  collapsableContainer.classList.toggle(closeClass);
  const showText = toggleElement.dataset.showText;
  const hideText = toggleElement.dataset.hideText;
  toggleElement.textContent = collapsableContainer.classList.contains(closeClass)
    ? showText
    : hideText;
}

const handleCollapsable = (e) => {
  toggleCollapse(e.target);
};

collapsableToggles.forEach(element => {
  if (element.dataset.maxHeightWhenClosed !== undefined) {
    // If a max height is set, then the element will be partially visible when closed,
    // but if the element's height is actually less than the max height, then no "colappsable" 
    // actions will take place and we hide the toggle element
    const collapsableContainer = document.getElementById(element.dataset.target);
    if (element.dataset.maxHeightWhenClosed >= collapsableContainer.clientHeight) {
      element.classList.add('display-none');  // Hide controls
      return; // continue to next toggle element as this will not implement collapsable behaviour
    }
  }
  
  if (element.dataset.hideOnLoad !== undefined){
    toggleCollapse(element);
  } else {
    element.textContent = element.dataset.hideText;
  }
  element.addEventListener('click', handleCollapsable);
});


