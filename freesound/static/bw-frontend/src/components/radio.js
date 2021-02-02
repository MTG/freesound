const radios = [...document.getElementsByClassName('bw-radio')];

const addVisibleCheckbox = radioEl => {
  const parent = radioEl.parentNode;
  const actualRadioIndex = [...parent.children].findIndex(el =>
    [...el.classList].includes('bw-radio')
  );
  const insertBeforeElement = [...parent.children][actualRadioIndex + 1];
  const visibleRadioContainer = document.createElement('span');
  visibleRadioContainer.className = 'bw-radio-container';
  parent.insertBefore(visibleRadioContainer, insertBeforeElement);
  const RadioIcon = document.createElement('span');
  RadioIcon.className = 'bw-icon-radio';
  visibleRadioContainer.append(RadioIcon);
};

radios.forEach(addVisibleCheckbox);
