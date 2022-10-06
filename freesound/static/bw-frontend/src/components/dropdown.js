// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const dropdownToggles = [...document.querySelectorAll('[data-toggle="dropdown"]')];

const lastOpenedDropdown = { toggle: undefined, dropdownOptions: undefined };

const closeOnClickAway = () => {
  const { toggle, dropdownOptions } = lastOpenedDropdown;
  if (toggle && dropdownOptions) {
    dropdownOptions.classList.remove('show');
    toggle.setAttribute('aria-expanded', 'false');
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
    toggle.setAttribute('aria-expanded', 'true');
    lastOpenedDropdown.toggle = toggle;
    lastOpenedDropdown.dropdownOptions = dropdownOptions;
    setTimeout(() => {
      // attach the close listener asynchronously to avoid closing it immediately
      document.body.addEventListener('click', closeOnClickAway);
    }, 0);
  }
};

dropdownToggles.forEach(toggle => {
  toggle.addEventListener('click', () => toggleExpandDropdown(toggle));
});

// @license-end
