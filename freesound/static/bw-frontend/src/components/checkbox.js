// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const addVisibleCheckbox = (checkboxEl) => {

    // We want <input type="checkbox" ...> elements to be inside their corresponding <label> element. When rendering
    // forms with Django, this is not always true, and sometimes the input element is positioned right after the
    // label element. Check if this is the case and re-position the checkbox element to be first child of label
    // element
    const labelEl = checkboxEl.previousElementSibling;
    if ((labelEl) && (labelEl.tagName === 'LABEL')){
        labelEl.prepend(checkboxEl);
    }

    // Add CSS class to the label element
    checkboxEl.parentNode.classList.add('bw-checkbox-label');

    // Create the visible version of checkbox element (if it has not been already created)
    let visibleElementAlreadyAdded = false;
    if ((checkboxEl.nextElementSibling !== null) && (checkboxEl.nextElementSibling.classList.contains('bw-checkbox-container'))){
        visibleElementAlreadyAdded = true;
    }
    if (!visibleElementAlreadyAdded){
        const visibleCheckboxContainer = document.createElement('span');
        visibleCheckboxContainer.className = 'bw-checkbox-container';
        checkboxEl.parentNode.insertBefore(visibleCheckboxContainer, checkboxEl.nextSibling);
        const checkboxIcon = document.createElement('span');
        checkboxIcon.className = 'bw-icon-checkbox';
        visibleCheckboxContainer.append(checkboxIcon);
    }
};

const addCheckboxVisibleElements = () => {
    const checkboxes = [...document.querySelectorAll('input.bw-checkbox')];
    checkboxes.forEach(addVisibleCheckbox);
};

addCheckboxVisibleElements();

export default addCheckboxVisibleElements;

// @license-end
