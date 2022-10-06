// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const radios = [...document.querySelectorAll('input.bw-radio')];

const addVisibleRadio = radioEl => {

  // We expect radio elements to be wrapped inside their corresponding <label> element.
  // We get the label element and add some styling
  const parent = radioEl.parentNode;
  parent.classList.add('bw-radio-label');

  // Now we add the visible version of the radio element
  let visibleElementAlreadyAdded = false;
  if ((radioEl.nextElementSibling !== null) && (radioEl.nextElementSibling.classList.contains('bw-radio-container'))){
    visibleElementAlreadyAdded = true;
  }
  if (!visibleElementAlreadyAdded){
    const visibleRadioContainer = document.createElement('span');
    visibleRadioContainer.className = 'bw-radio-container';
    parent.insertBefore(visibleRadioContainer, radioEl.nextSibling);
    const RadioIcon = document.createElement('span');
    RadioIcon.className = 'bw-icon-radio-unchecked';
    visibleRadioContainer.append(RadioIcon);
  }

};

radios.forEach(addVisibleRadio);

// @license-end
