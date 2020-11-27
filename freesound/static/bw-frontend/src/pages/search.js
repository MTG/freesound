import './page-polyfills';
import throttle from "lodash.throttle";
import navbar from "../components/navbar";

// Main search input box behaviour
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