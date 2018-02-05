const dropdownToggles = [...document.querySelectorAll('[data-toggle="dropdown"]')];

const lastOpenedDropdown = { toggle: undefined, dropdownOptions: undefined };

const closeOnClickAway = () => {
  const { toggle, dropdownOptions } = lastOpenedDropdown;
  if (toggle && dropdownOptions) {
    dropdownOptions.classList.remove('show');
    toggle.setAttribute('aria-expanded', 'false');
  }
  document.body.removeEventListener('click', closeOnClickAway);
};

const toggleExpandDropdown = toggle => {
  const dropdownContainer = toggle.closest('.dropdown');
  const isDropdownExpanded = toggle.getAttribute('aria-expanded') === 'true';
  if (!dropdownContainer) {
    return;
  }
  const dropdownOptions = dropdownContainer.getElementsByClassName('dropdown-menu')[0];
  if (dropdownOptions) {
    if (isDropdownExpanded) {
      dropdownOptions.classList.remove('show');
      toggle.setAttribute('aria-expanded', 'false');
    } else {
      dropdownOptions.classList.add('show');
      toggle.setAttribute('aria-expanded', 'true');
      lastOpenedDropdown.toggle = toggle;
      lastOpenedDropdown.dropdownOptions = dropdownOptions;
      setTimeout(() => {
        // attach the close listener asynchronously to avoid closing it immediately
        document.body.addEventListener('click', closeOnClickAway);
      }, 0);
    }
  }
};

dropdownToggles.forEach(toggle => {
  toggle.addEventListener('click', () => toggleExpandDropdown(toggle));
});
