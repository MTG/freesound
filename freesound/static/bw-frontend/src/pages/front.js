import './page-polyfills';
import throttle from 'lodash.throttle';
import navbar from '../components/navbar';
import { addTypeAheadFeatures } from '../components/typeahead';
import wait from '../utils/wait';

// Main search input box behaviour

const fetchSuggestions = async inputElement => {
  const query = inputElement.value;
  let response = await fetch(
    `${inputElement.dataset.typeaheadSuggestionsUrl}?q=${query}`
  );
  let data = await response.json();
  const suggestions = data.suggestions;
  suggestions.forEach(suggestion => {
    suggestion.label = '<div class="padding-1">' + suggestion.value + '</div>';
  });
  return suggestions;
};

addTypeAheadFeatures(
  document.getElementById('search-sounds'),
  fetchSuggestions,
  (suggestion, suggestionsWrapper, inputElement) => {
    suggestionsWrapper.classList.add('hidden');
    inputElement.value = suggestion.value;
    inputElement.blur();
    setTimeout(() => {
      // Add timeout so that input has time to update before form is submitted
      inputElement.form.submit();
    }, 50);
  }
);

// Navbar search input box behaviour  (shouold only appear when heroSearch is not visible)
const heroSearch = document.getElementsByClassName('bw-front__hero-search')[0];
const SCROLL_CHECK_TIMER = 100; // min interval (in ms) between consecutive calls of scroll checking function
const checkShouldShowSearchInNavbar = throttle(() => {
  const heroRect = heroSearch.getBoundingClientRect();
  // not all browsers support clientRect.height
  const heroSearchPosition = heroRect.height
    ? heroRect.y + heroRect.height
    : heroRect.y;
  const shouldShowSearchBar = heroSearchPosition < 80;
  const isShowingSearchBar = !navbar.classList.contains('bw-nav--expanded');
  if (shouldShowSearchBar !== isShowingSearchBar) {
    navbar.classList.toggle('bw-nav--expanded');
  }
}, SCROLL_CHECK_TIMER);

window.addEventListener('scroll', checkShouldShowSearchInNavbar);
