import debounce from 'lodash.debounce';

const updateObjectSelectorDataProperties = (selectorElement, callback) => {
  const objectCheckboxes =
    selectorElement.querySelectorAll('input.bw-checkbox');
  const selectedIds = [];
  const unselectedIds = [];
  objectCheckboxes.forEach(checkbox => {
    if (checkbox.checked) {
      selectedIds.push(checkbox.dataset.objectId);
    } else {
      unselectedIds.push(checkbox.dataset.objectId);
    }
  });
  selectorElement.dataset.selectedIds = selectedIds.join(',');
  selectorElement.dataset.unselectedIds = unselectedIds.join(',');
  if (callback !== undefined) {
    callback(selectorElement);
  }
};

const debouncedUpdateObjectSelectorDataProperties = debounce(
  updateObjectSelectorDataProperties,
  100,
  { trailing: true }
);

const initializeObjectSelector = (selectorElement, onChangeCallback) => {
  // Note this can be safely called multiple times on the same selectorElement as event listeners will only be added if not already added
  // Also note that if called multiple times, only the first passed onChangeCallback will remain active
  const debouncedOnChangeCallback = debounce(onChangeCallback);
  const selectableObjectElements = [
    ...selectorElement.getElementsByClassName('bw-selectable-object'),
  ];
  selectableObjectElements.forEach(element => {
    const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
    if (checkbox.dataset.initialized === undefined) {
      debouncedUpdateObjectSelectorDataProperties(
        element.parentNode.parentNode
      );
      checkbox.dataset.initialized = true; // Avoid re-initializing multiple times the same object
      checkbox.addEventListener('change', evt => {
        if (checkbox.checked) {
          element.classList.add('selected');
        } else {
          element.classList.remove('selected');
        }
        debouncedUpdateObjectSelectorDataProperties(
          element.parentNode.parentNode,
          debouncedOnChangeCallback
        );
      });
    }
  });

  // Configure select all/none buttons
  const selectAllSelectNoneButtons =
    selectorElement.parentNode.getElementsByClassName('select-button');
  if (selectAllSelectNoneButtons.length == 2) {
    const selectAllButton = selectAllSelectNoneButtons[0];
    const selectNoneButton = selectAllSelectNoneButtons[1];
    selectAllButton.addEventListener('click', evt => {
      selectableObjectElements.forEach(element => {
        const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
        checkbox.checked = true;
        if (checkbox.checked) {
          element.classList.add('selected');
        } else {
          element.classList.remove('selected');
        }
        debouncedUpdateObjectSelectorDataProperties(
          element.parentNode.parentNode,
          debouncedOnChangeCallback
        );
      });
    });
    selectNoneButton.addEventListener('click', evt => {
      selectableObjectElements.forEach(element => {
        const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
        checkbox.checked = false;
        if (checkbox.checked) {
          element.classList.add('selected');
        } else {
          element.classList.remove('selected');
        }
        debouncedUpdateObjectSelectorDataProperties(
          element.parentNode.parentNode,
          debouncedOnChangeCallback
        );
      });
    });
  }
};
export { initializeObjectSelector, updateObjectSelectorDataProperties };
