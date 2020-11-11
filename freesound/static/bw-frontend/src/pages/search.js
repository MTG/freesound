import './page-polyfills';

const searchInputBrowse = document.getElementById('search-input-browse');
const removeSearchInputValueBrowse = document.getElementById('remove-content-search');

const searchInputChange = event => {
  if (event.target.value.length) {
    removeSearchInputValueBrowse.style.opacity = 0.5;
  } else {
    removeSearchQuery();
  }
};

const removeSearchQuery = () => {
  searchInputBrowse.value = '';
  removeSearchInputValueBrowse.style.opacity = 0;
};

searchInputBrowse.addEventListener('input', searchInputChange);
removeSearchInputValueBrowse.addEventListener('click', removeSearchQuery);
