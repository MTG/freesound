function makeSelect(container) {
  var select = container.getElementsByTagName('select'),
    liElement,
    ulElement,
    optionValue,
    iElement,
    optionText,
    selectDropdown,
    elementParentSpan;

  for (var select_i = 0, len = select.length; select_i < len; select_i++) {
    // Check if select element already wrapped, otherwise wrap the element, make it invisible and create new visible version
    const selectElement = select[select_i];
    const alreadyWrapped =
      selectElement.parentElement.classList.contains('select-dropdown');
    if (!alreadyWrapped) {
      let selected_index_text = '';
      if (selectElement.selectedIndex > -1) {
        selected_index_text =
          selectElement.options[selectElement.selectedIndex].text;
      } else {
        selected_index_text = selectElement.options[0].text;
      }

      selectElement.style.display = 'none';
      const wrapper = wrapElement(
        selectElement,
        document.createElement('div'),
        select_i,
        selected_index_text
      );

      for (var i = 0; i < selectElement.options.length; i++) {
        liElement = document.createElement('li');
        optionValue = selectElement.options[i].value;
        optionText = document.createTextNode(selectElement.options[i].text);
        liElement.className = 'select-dropdown__list-item';
        if (selectElement.dataset.greyItems !== undefined) {
          if (
            selectElement.dataset.greyItems
              .split(',')
              .indexOf(optionValue.toString()) > -1
          ) {
            liElement.className += ' text-grey';
          }
        }
        liElement.setAttribute('data-value', optionValue);
        liElement.appendChild(optionText);
        ulElement.appendChild(liElement);
        liElement.addEventListener(
          'click',
          function () {
            displayUl(this);
          },
          false
        );
      }

      const selectWithKeyboard =
        selectElement.dataset.selectWithKeyboard !== undefined;
      if (selectWithKeyboard) {
        let clearCurrentKeysTimeout = undefined;
        let currentKeysPressed = '';
        document.addEventListener('keydown', evt => {
          ulElement = wrapper.getElementsByTagName('ul')[0];
          if (ulElement.classList.contains('active')) {
            if (['ArrowUp', 'ArrowDown', 'Enter'].indexOf(evt.key) > -1) {
              if (evt.key === 'ArrowUp') {
                // Pre-select element on top
                const previousLiElement = getPreviousLiElementIfAny(
                  ulElement,
                  getPreSelectedLiElement(ulElement)
                );
                preSelectLiElement(previousLiElement);
              } else if (evt.key === 'ArrowDown') {
                // Pre-select element on top
                const currentPreSelectedElement =
                  getPreSelectedLiElement(ulElement);
                const nextLiElement = getNextLiElementIfAny(
                  ulElement,
                  currentPreSelectedElement
                );
                preSelectLiElement(nextLiElement);
              } else {
                // Enter (select the pre-selected element)
                const liElement = getPreSelectedLiElement(ulElement);
                if (liElement !== undefined) {
                  displayUl(liElement);
                }
              }
            } else {
              currentKeysPressed += evt.key;
              Array.from(ulElement.children).every(liElement => {
                if (
                  liElement.innerHTML
                    .toLowerCase()
                    .startsWith(currentKeysPressed.toLowerCase())
                ) {
                  preSelectLiElement(liElement);
                  return false;
                }
                return true;
              });
              if (clearCurrentKeysTimeout !== undefined) {
                window.clearTimeout(clearCurrentKeysTimeout);
              }
              clearCurrentKeysTimeout = setTimeout(() => {
                currentKeysPressed = '';
              }, 500);
            }
            evt.stopPropagation();
            evt.preventDefault();
          }
        });
      }
    }
  }

  function wrapElement(el, wrapper, i, placeholder) {
    el.parentNode.insertBefore(wrapper, el);
    wrapper.appendChild(el);

    document.addEventListener('click', function (e) {
      let clickInside = wrapper.contains(e.target);
      if (!clickInside) {
        let menu = wrapper.getElementsByClassName('select-dropdown__list')[0];
        menu.classList.remove('active');
        removeActiveClassFromAllLiElements(menu);
      }
    });

    var buttonElement = document.createElement('button'),
      spanElement = document.createElement('span'),
      spanText = document.createTextNode(placeholder);
    iElement = document.createElement('i');
    ulElement = document.createElement('ul');

    wrapper.className = 'select-dropdown select-dropdown--' + i;
    buttonElement.className =
      'select-dropdown__button select-dropdown__button--' + i;
    buttonElement.setAttribute('data-value', '');
    buttonElement.setAttribute('type', 'button');
    if (el.getAttribute('disabled') !== null) {
      buttonElement.setAttribute('disabled', 'disabled');
      buttonElement.classList.add('opacity-020');
    }
    spanElement.className = 'select-dropdown select-dropdown--' + i;
    iElement.className = 'zmdi bw-icon-chevron-up bw-select__chevron';
    ulElement.className = 'select-dropdown__list select-dropdown__list--' + i;
    ulElement.id = 'select-dropdown__list-' + i;

    wrapper.appendChild(buttonElement);
    spanElement.appendChild(spanText);
    buttonElement.appendChild(spanElement);
    buttonElement.appendChild(iElement);
    wrapper.appendChild(ulElement);
    return wrapper;
  }

  function displayUl(element) {
    var select =
      element.parentNode.parentNode.getElementsByTagName('select')[0];
    if (element.tagName == 'BUTTON') {
      selectDropdown = element.parentNode.getElementsByTagName('ul')[0];
      selectDropdown.classList.toggle('active');
      // Pre-select the already selected element
      for (var i = 0; i < selectDropdown.children.length; i++) {
        const liElement = selectDropdown.children[i];
        if (liElement.dataset.value === select.value) {
          preSelectLiElement(liElement);
        }
      }
    } else if (element.tagName == 'LI') {
      selectElement(select, element);
    }
  }

  function removeActiveClassFromAllLiElements(ulElement) {
    Array.from(ulElement.children).forEach(liElement => {
      liElement.classList.remove('active');
    });
  }

  function getPreSelectedLiElement(ulElement) {
    return ulElement.getElementsByClassName('active')[0];
  }

  function getPreviousLiElementIfAny(ulElement, liElement) {
    if (liElement === undefined) {
      return ulElement.children[ulElement.children.length - 1];
    }
    const index = Array.from(ulElement.children).indexOf(liElement);
    if (index > 0) {
      return ulElement.children[index - 1];
    } else {
      return ulElement.children[index];
    }
  }

  function getNextLiElementIfAny(ulElement, liElement) {
    if (liElement === undefined) {
      return ulElement.children[0];
    }
    const index = Array.from(ulElement.children).indexOf(liElement);
    if (Array.from(ulElement.children).length > index + 1) {
      return ulElement.children[index + 1];
    } else {
      return ulElement.children[index];
    }
  }

  function preSelectLiElement(liElement) {
    const ulElement = liElement.parentNode;
    removeActiveClassFromAllLiElements(ulElement);
    liElement.classList.add('active');
    const topPos = liElement.offsetTop;
    ulElement.scrollTop = topPos - 20;
  }

  function selectElement(select, selectedLiElement) {
    // Update underlying select element with new value
    select.value = selectedLiElement.getAttribute('data-value');

    // Trigger change event manually (setting the value programatically does not trigger the event)
    select.dispatchEvent(new Event('change'));

    // Update the "fake" select
    const elementParentSpan =
      selectedLiElement.parentNode.parentNode.getElementsByTagName('span')[0];
    selectedLiElement.parentNode.classList.toggle('active');
    elementParentSpan.textContent = selectedLiElement.textContent;
    elementParentSpan.parentNode.setAttribute(
      'data-value',
      selectedLiElement.getAttribute('data-value')
    );
    removeActiveClassFromAllLiElements(selectedLiElement.parentNode);
  }

  var buttonSelect = document.getElementsByClassName('select-dropdown__button');
  for (
    var buttonIndex = 0, buttonLen = buttonSelect.length;
    buttonIndex < buttonLen;
    buttonIndex++
  ) {
    if (!buttonSelect[buttonIndex].hasAttribute('data-listener-added')) {
      // Only add the listener if it has not already been added
      buttonSelect[buttonIndex].setAttribute('data-listener-added', true);
      buttonSelect[buttonIndex].addEventListener(
        'click',
        function (e) {
          e.preventDefault();
          displayUl(this);
        },
        false
      );
    }
  }
}

export { makeSelect };
