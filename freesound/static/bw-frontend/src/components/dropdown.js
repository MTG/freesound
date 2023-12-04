const lastOpenedDropdown = { toggle: undefined, dropdownOptions: undefined };

const closeOnClickAway = () => {
  const { toggle, dropdownOptions } = lastOpenedDropdown;
  if (toggle && dropdownOptions) {
    dropdownOptions.classList.remove('show');
    toggle.ariaExpanded = 'false';
    lastOpenedDropdown.toggle = undefined;
    lastOpenedDropdown.dropdownOptions = undefined;
  }
  document.body.removeEventListener('click', closeOnClickAway);
};

const toggleExpandDropdown = toggle => {
  const dropdownContainer = toggle.closest('.dropdown');
  const isDropdownExpanded = lastOpenedDropdown.toggle && lastOpenedDropdown.toggle === toggle;
  const isSomeOtherDropdownExpanded =
    lastOpenedDropdown.toggle && lastOpenedDropdown.toggle !== toggle;

  const shouldCloseLastOpenedDropdown = isDropdownExpanded || isSomeOtherDropdownExpanded;
  if (shouldCloseLastOpenedDropdown) {
    closeOnClickAway();
  }
  if (!dropdownContainer) {
    return;
  }
  const dropdownOptions = dropdownContainer.getElementsByClassName('dropdown-menu')[0];
  if (dropdownOptions && !isDropdownExpanded) {
    dropdownOptions.classList.add('show');
    toggle.ariaExpanded = 'true';
    lastOpenedDropdown.toggle = toggle;
    lastOpenedDropdown.dropdownOptions = dropdownOptions;
    setTimeout(() => {
      // attach the close listener asynchronously to avoid closing it immediately
      document.body.addEventListener('click', closeOnClickAway);
    }, 0);
  }
};

const makeDropdowns = (container) => {
  const dropdownToggles = [...container.querySelectorAll('[data-toggle="dropdown"]')];
  dropdownToggles.forEach(toggle => {
    toggle.ariaExpanded = 'false';
    toggle.ariaHasPopup = 'menu';
    const dropdownContainer = toggle.closest('.dropdown');
    const dropdownOptions = dropdownContainer.getElementsByClassName('dropdown-menu')[0];
    dropdownOptions.setAttribute('role', 'menu');
    dropdownOptions.getElementsByClassName('dropdown-item').forEach(item => {
      item.setAttribute('role', 'menuitem');
    });
    toggle.addEventListener('click', () => toggleExpandDropdown(toggle));
  });
}

export {makeDropdowns};
