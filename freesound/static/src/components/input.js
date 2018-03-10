import { getIcon } from '../utils/icons';

const searchBoxes = [...document.querySelectorAll('input[type="search"]')];

searchBoxes.forEach(searchField => {
  const inputWrapper = searchField.parentNode;
  const searchSvg = getIcon('search');
  const searchIconNode = searchSvg;
  inputWrapper.insertBefore(searchIconNode, searchField);
  const renderedSvgIcon = inputWrapper.getElementsByTagName('svg')[0];
  if (renderedSvgIcon) {
    renderedSvgIcon.setAttribute('class', 'input-icon');
  }
});
