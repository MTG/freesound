const addVisibleRadio = radioEl => {
  // We expect radio elements to be wrapped inside their corresponding <label> element.
  // We get the label element and add some styling
  const parent = radioEl.parentNode;
  parent.classList.add('bw-radio-label');

  // Now we add the visible version of the radio element
  let visibleElementAlreadyAdded = false;
  if (
    radioEl.nextElementSibling !== null &&
    radioEl.nextElementSibling.classList.contains('bw-radio-container')
  ) {
    visibleElementAlreadyAdded = true;
  }
  if (!visibleElementAlreadyAdded) {
    const visibleRadioContainer = document.createElement('span');
    visibleRadioContainer.className = 'bw-radio-container';
    parent.insertBefore(visibleRadioContainer, radioEl.nextSibling);
    const radioIcon = document.createElement('span');
    radioIcon.className = 'bw-icon-radio-unchecked';
    radioIcon.setAttribute('role', 'radio');
    radioIcon.setAttribute('aria-checked', radioEl.checked);
    radioEl.addEventListener('change', () => {
      const radioOptions = document.getElementsByName(radioEl.name);
      radioOptions.forEach(option => {
        option.parentNode
          .getElementsByClassName('bw-icon-radio-unchecked')[0]
          .setAttribute('aria-checked', false);
      });
      radioIcon.setAttribute('aria-checked', radioEl.checked);
    });
    visibleRadioContainer.append(radioIcon);
  }
};

const makeRadios = container => {
  const radios = [...container.querySelectorAll('input.bw-radio')];
  radios.forEach(addVisibleRadio);
};

export { makeRadios };
