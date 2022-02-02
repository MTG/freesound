function createSelect() {
  var select = document.getElementsByTagName('select'),
    liElement,
    ulElement,
    optionValue,
    iElement,
    optionText,
    selectDropdown,
    elementParentSpan;

  for (var select_i = 0, len = select.length; select_i < len; select_i++) {
    // Check if select element already wrapped, otherwise wrap the element, make it invisible and create new visible version
    const alreadyWrapped = select[select_i].parentElement.classList.contains('select-dropdown');
    if (!alreadyWrapped){
      select[select_i].style.display = 'none';
      wrapElement(
        document.getElementById(select[select_i].id),
        document.createElement('div'),
        select_i,
        select[select_i].options[select[select_i].selectedIndex].text
      );

      for (var i = 0; i < select[select_i].options.length; i++) {
        liElement = document.createElement('li');
        optionValue = select[select_i].options[i].value;
        optionText = document.createTextNode(select[select_i].options[i].text);
        liElement.className = 'select-dropdown__list-item';
        liElement.setAttribute('data-value', optionValue);
        liElement.appendChild(optionText);
        ulElement.appendChild(liElement);

        liElement.addEventListener(
          'click',
          function() {
            displyUl(this);
          },
          false
        );
      }
    }
  }

  function wrapElement(el, wrapper, i, placeholder) {
    el.parentNode.insertBefore(wrapper, el);
    wrapper.appendChild(el);

    document.addEventListener('click', function(e) {
      let clickInside = wrapper.contains(e.target);
      if (!clickInside) {
        let menu = wrapper.getElementsByClassName('select-dropdown__list');
        menu[0].classList.remove('active');
      }
    });

    var buttonElement = document.createElement('button'),
      spanElement = document.createElement('span'),
      spanText = document.createTextNode(placeholder);
    iElement = document.createElement('i');
    ulElement = document.createElement('ul');

    wrapper.className = 'select-dropdown select-dropdown--' + i;
    buttonElement.className = 'select-dropdown__button select-dropdown__button--' + i;
    buttonElement.setAttribute('data-value', '');
    buttonElement.setAttribute('type', 'button');
    spanElement.className = 'select-dropdown select-dropdown--' + i;
    iElement.className = 'zmdi bw-icon-chevron-up bw-select__chevron';
    ulElement.className = 'select-dropdown__list select-dropdown__list--' + i;
    ulElement.id = 'select-dropdown__list-' + i;

    wrapper.appendChild(buttonElement);
    spanElement.appendChild(spanText);
    buttonElement.appendChild(spanElement);
    buttonElement.appendChild(iElement);
    wrapper.appendChild(ulElement);
  }

  function displyUl(element) {
    if (element.tagName == 'BUTTON') {
      selectDropdown = element.parentNode.getElementsByTagName('ul');
      //var labelWrapper = document.getElementsByClassName('js-label-wrapper');
      for (var i = 0, len = selectDropdown.length; i < len; i++) {
        selectDropdown[i].classList.toggle('active');
        //var parentNode = $(selectDropdown[i]).closest('.js-label-wrapper');
        //parentNode[0].classList.toggle("active");
      }
    } else if (element.tagName == 'LI') {
      var selectId = element.parentNode.parentNode.getElementsByTagName('select')[0];
      selectElement(selectId.id, element.getAttribute('data-value'));
      elementParentSpan = element.parentNode.parentNode.getElementsByTagName('span');
      element.parentNode.classList.toggle('active');
      elementParentSpan[0].textContent = element.textContent;
      elementParentSpan[0].parentNode.setAttribute(
        'data-value',
        element.getAttribute('data-value')
      );
    }
  }

  function selectElement(id, valueToSelect) {
    // Update underlying select element with new value
    var element = document.getElementById(id);
    element.value = valueToSelect;

    // Trigger change event manually (setting the value programatically does not trigger the event)
    var event = document.createEvent('HTMLEvents');
    event.initEvent('change', true, false);
    element.dispatchEvent(event);
  }

  var buttonSelect = document.getElementsByClassName('select-dropdown__button');
  for (var i = 0, len = buttonSelect.length; i < len; i++) {
    if (!buttonSelect[i].hasAttribute('data-listener-added')){
      // Only add the listener if it has not already been added
      buttonSelect[i].setAttribute('data-listener-added', true);
      buttonSelect[i].addEventListener(
        'click',
        function(e) {
          e.preventDefault();
          displyUl(this);
        },
        false
      );
    }
  }
}

createSelect();

export {createSelect};
