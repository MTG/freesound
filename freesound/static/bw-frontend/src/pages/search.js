import './page-polyfills';
import throttle from "lodash.throttle";
import navbar from "../components/navbar";

// Main search input box behaviour
const searchInputBrowse = document.getElementById('search-input-browse');
const searchInputBrowsePlaceholder = searchInputBrowse.getAttribute("placeholder");
const removeSearchInputValueBrowse = document.getElementById('remove-content-search');


const updateRemoveSearchInputButtonVisibility = (searchInputElement) => {
  if (searchInputElement.value.length) {
    removeSearchInputValueBrowse.style.opacity = 0.5;
  } else {
    removeSearchInputValueBrowse.style.opacity = 0.0;
  }
}

const updateSearchInput = (event) => {
  var element = event.target;
  if (element === document.activeElement){  // Element has focus
    // Remove placeholder attribute so it does not show under the blinking caret when no text has been entered yet
    element.setAttribute('placeholder', '');
    updateRemoveSearchInputButtonVisibility(element);
  } else {  // Element has no focus
    // Set placeholder attribute back to the original
    element.setAttribute('placeholder', searchInputBrowsePlaceholder);
  }
}

const removeSearchQuery = () => {
  removeSearchInputValueBrowse.style.opacity = 0;
  searchInputBrowse.value = '';
  searchInputBrowse.focus();
};

removeSearchInputValueBrowse.addEventListener('click', removeSearchQuery);
searchInputBrowse.addEventListener('input', updateSearchInput);
searchInputBrowse.addEventListener('focus', updateSearchInput);
searchInputBrowse.addEventListener('blur', updateSearchInput);
window.addEventListener('load', function(){updateRemoveSearchInputButtonVisibility(searchInputBrowse)})

// Navbar search input box behaviour (shouold only appear when searchInputBrowse is not visible)
const SCROLL_CHECK_TIMER = 100 // min interval (in ms) between consecutive calls of scroll checking function
const checkShouldShowSearchInNavbar = throttle(() => {
  const heroRect = searchInputBrowse.getBoundingClientRect()
  // not all browsers support clientRect.height
  const heroSearchPosition = heroRect.height
    ? heroRect.y + heroRect.height
    : heroRect.y
  const shouldShowSearchBar = heroSearchPosition < 80
  const isShowingSearchBar = !navbar.classList.contains('bw-nav--expanded')
  if (shouldShowSearchBar !== isShowingSearchBar) {
    navbar.classList.toggle('bw-nav--expanded')
  }
}, SCROLL_CHECK_TIMER)

window.addEventListener('scroll', checkShouldShowSearchInNavbar)