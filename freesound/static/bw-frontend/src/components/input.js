import { createIconElement } from '../utils/icons';

const addSearchIconToInputs = container => {
  const searchBoxes = [...container.querySelectorAll('input[type="search"]')];
  searchBoxes.forEach(searchField => {
    const inputWrapper = searchField.parentNode;
    const searchIconNode = createIconElement('bw-icon-search');
    searchIconNode.classList.add('input-icon');
    inputWrapper.insertBefore(searchIconNode, searchField);
  });
};

export { addSearchIconToInputs };
