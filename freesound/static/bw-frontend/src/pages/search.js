import './page-polyfills';

const searchInputBrowse = document.getElementById('search-input-browse');
const removeSearchInputValueBrowse = document.getElementById('remove-content-search');

const searchInputChange = event => {
  if (event.target.value.length) {
    removeSearchInputValueBrowse.style.opacity = 0.5;
  }
};

const removeSearchQuery = () => {
  searchInputBrowse.value = '';
  removeSearchInputValueBrowse.style.opacity = 0;
};

searchInputBrowse.addEventListener('change', searchInputChange);
removeSearchInputValueBrowse.addEventListener('click', removeSearchQuery);
