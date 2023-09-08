import './page-polyfills';
import throttle from "lodash.throttle";
import navbar from "../components/navbar";

// Main search input box behaviour
const searchInputBrowse = document.getElementById('search-input-browse');
const tagsModeInput = document.getElementById('tags-mode');
const tagsMode = tagsModeInput.value == '1';
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

// Navbar search input box behaviour (should only appear when searchInputBrowse is not visible)
const searchFormIsVisible = () => {

  let heroRect;
  if (advancedSearchOptionsIsVisible()){
    // If advanced search options is expanded, use that as heroRect to check if search form is visible
    heroRect = advanced_search_options_div.getBoundingClientRect()
  } else {
    if (!tagsMode){
      heroRect = searchInputBrowse.getBoundingClientRect()
    } else {
      heroRect = document.getElementById('tags-mode-input-section').getBoundingClientRect()
    }
  }
  
  // not all browsers support clientRect.height
  const heroSearchPosition = heroRect.height
    ? heroRect.y + heroRect.height
    : heroRect.y
  return heroSearchPosition >= 80;
}

const SCROLL_CHECK_TIMER = 100 // min interval (in ms) between consecutive calls of scroll checking function
const checkShouldShowSearchInNavbar = throttle(() => {
  const shouldShowSearchBar = tagsMode === true ? true : !searchFormIsVisible();
  const isShowingSearchBar = !navbar.classList.contains('bw-nav--expanded');
  if (shouldShowSearchBar !== isShowingSearchBar) {
    navbar.classList.toggle('bw-nav--expanded');
  }
}, SCROLL_CHECK_TIMER)

window.addEventListener('scroll', checkShouldShowSearchInNavbar)

/*
  ADVANCED SEARCH STUFF
  The functions below correspond to the javascript bits for handling the advanced search options
  The JS code is old and probably doing things in wrong ways (and more complex that it should)
  This should be completely refactored, but to avoid changes in backend and for compatibility between
  BeastWhoosh and Nightingale interfaces, we leave everything as is for now (just with small updates to
  avoid using JQuery).
*/

var search_form_element = document.getElementById('search_form');
var search_page_navbar_form = document.getElementById('search-page-navbar-form');
var advanced_search_options_div = document.getElementById('advanced-search-options');
var toggle_advanced_search_options_element = document.getElementById('toggle_advanced_search_options');
var sort_by_element = document.getElementsByName('s')[0];


function advancedSearchOptionsIsVisible()
{
  return !advanced_search_options_div.classList.contains('display-none');
}

function updateToggleAdvancedSearchOptionsText()
{
  if (advancedSearchOptionsIsVisible()){
    toggle_advanced_search_options_element.innerHTML = 'Hide advanced search options';
  } else {
    toggle_advanced_search_options_element.innerHTML = 'Show advanced search options';
  }
}

function showAdvancedSearchOptions()
{
  advanced_search_options_div.classList.remove('display-none');
  updateToggleAdvancedSearchOptionsText();
}

function hideAdvancedSearchOptions()
{
  advanced_search_options_div.classList.add('display-none');
  updateToggleAdvancedSearchOptionsText();
}

function toggleAdvancedSearchOptions(){
  if (advancedSearchOptionsIsVisible()){
    hideAdvancedSearchOptions();
  } else {
    showAdvancedSearchOptions();
  }
}

toggle_advanced_search_options_element.addEventListener('click', toggleAdvancedSearchOptions);


document.addEventListener('DOMContentLoaded', ()=>{
  // Update the text of the button to toggle advanced search options panel
  updateToggleAdvancedSearchOptionsText();

  // Store values of advanced search filters so later we can check if they were modified
  initialAdvancedSearchInputValues = serializeAdvanceSearchOptionsInputsData();
});

sort_by_element.addEventListener('change', function() {
  search_form_element.submit();
})

document.body.addEventListener('keydown',  evt => {
  const ENTER_KEY = 13
  if(evt.keyCode === ENTER_KEY){
    // If ENTER key is pressed and search form is visible, trigger form submission
    if (searchFormIsVisible()){
      search_form_element.submit();
    }
  }
})

if (search_page_navbar_form !== null){
  search_page_navbar_form.addEventListener('submit', function(evt){
    // Prevent default form submission
    if (evt.preventDefault) evt.preventDefault();
  
    // Copy input element contents to the main input element and do submission of the main form instead of the navbar one
    const searchInputBrowseNavbar = document.getElementById('search-input-browse-navbar');
    searchInputBrowse.value = searchInputBrowseNavbar.value;
    search_form_element.submit();
  
    // It is also needed to return false to prevent default form submission
    return false;
  })
}

// Enable/disable "apply advanced search filters" when filters are modified

const serializeAdvanceSearchOptionsInputsData = () => {
  const values = [];
  advanced_search_options_div.getElementsByTagName("input").forEach(inputElement => {
    if (inputElement.type == "hidden"){
      // Don't include hidden elements as only the visible items are necessary
    } else if (inputElement.type == "checkbox"){
      values.push(inputElement.checked);
    } else {
      values.push(inputElement.value);
    }
  });
  return values.join(",");
}

let initialAdvancedSearchInputValues = undefined;  // NOTE: this is filled out in onDocumentReady function

const advancedSearchOptionsHaveChangedSinceLastQuery = () => {
  const currentAdvancedSearchInputValues = serializeAdvanceSearchOptionsInputsData();
  return initialAdvancedSearchInputValues != currentAdvancedSearchInputValues;
}

const onAdvancedSearchOptionsInputsChange = () => {
  document.getElementById('avanced-search-apply-button').disabled = !advancedSearchOptionsHaveChangedSinceLastQuery();
}

advanced_search_options_div.getElementsByTagName("input").forEach(inputElement => {
  inputElement.addEventListener('change', evt => {
    onAdvancedSearchOptionsInputsChange();
  });
  inputElement.addEventListener('input', evt => {
    onAdvancedSearchOptionsInputsChange();
  });
});

// Create hidden elements for checkboxes that require knowing if they were submitted even if they are not checked
const addHiddenCheckboxesForAddHiddenElements = () => {
  [...document.querySelectorAll('input.bw-checkbox-add-hidden')].forEach(checkboxEl => {
      const newElementId = checkboxEl.id + '-hidden';
      if (document.getElementById(newElementId) === null){
          const newElement = document.createElement('input');
          newElement.type = 'hidden';
          newElement.id = newElementId;
          newElement.name = checkboxEl.dataset.hiddenCheckboxName;
          newElement.value = '1';
          checkboxEl.parentNode.insertBefore(newElement, checkboxEl);
      }
  });
};
addHiddenCheckboxesForAddHiddenElements();