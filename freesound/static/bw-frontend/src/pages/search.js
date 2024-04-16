import './page-polyfills';
import throttle from "lodash.throttle";
import navbar from "../components/navbar";

// Main search input box behaviour
const searchInputBrowse = document.getElementById('search-input-browse');
const searchInputBrowsePlaceholder = searchInputBrowse.getAttribute("placeholder");
const removeSearchInputValueBrowse = document.getElementById('remove-content-search');
const advancedSearchOptionsDiv = document.getElementById('advanced-search-options');
const tagsMode = location.pathname.indexOf('/browse/tags/') > -1;

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
    heroRect = advancedSearchOptionsDiv.getBoundingClientRect()
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

// Advanced search options behaviour

const toggleAdvancedSearchOptionsElement = document.getElementById('toggle_advanced_search_options');

function advancedSearchOptionsIsVisible()
{
  return advancedSearchOptionsDiv.dataset.visible === "1";
}

function updateToggleAdvancedSearchOptionsText()
{
  if (advancedSearchOptionsIsVisible()){
    toggleAdvancedSearchOptionsElement.innerHTML = 'Hide advanced search options';
  } else {
    toggleAdvancedSearchOptionsElement.innerHTML = 'Show advanced search options';
  }
}

function showAdvancedSearchOptions()
{
  advancedSearchOptionsDiv.dataset.visible = "1";
  advancedSearchOptionsDiv.style.display = 'block';
  updateToggleAdvancedSearchOptionsText();
}

function hideAdvancedSearchOptions()
{
  advancedSearchOptionsDiv.dataset.visible = "0";
  advancedSearchOptionsDiv.style.display = 'none';
  updateToggleAdvancedSearchOptionsText();
}

function toggleAdvancedSearchOptions(){
  if (advancedSearchOptionsIsVisible()){
    hideAdvancedSearchOptions();
  } else {
    showAdvancedSearchOptions();
  }
}

toggleAdvancedSearchOptionsElement.addEventListener('click', toggleAdvancedSearchOptions);

// Track changes in advanced search options

let initialAdvancedSearchInputValues = undefined;  // NOTE: this is filled out in onDocumentReady function

const serializeAdvanceSearchOptionsInputsData = () => {
  const values = [];
  advancedSearchOptionsDiv.getElementsByTagName("input").forEach(inputElement => {
    if (inputElement.type == "hidden"){
      // Don't include hidden elements as only the visible items are necessary
    } else if (inputElement.type == "checkbox"){
      values.push(inputElement.checked);
    } else {
      values.push(inputElement.value);
    }
  });
  advancedSearchOptionsDiv.getElementsByTagName("select").forEach(selectElement => {
    values.push(selectElement.value);
  });
  return values.join(",");
}

const advancedSearchOptionsHaveChangedSinceLastQuery = () => {
  const currentAdvancedSearchInputValues = serializeAdvanceSearchOptionsInputsData();
  return initialAdvancedSearchInputValues != currentAdvancedSearchInputValues;
}

const onAdvancedSearchOptionsInputsChange = () => {
  document.getElementById('avanced-search-apply-button').disabled = !advancedSearchOptionsHaveChangedSinceLastQuery();
}

advancedSearchOptionsDiv.getElementsByTagName("input").forEach(inputElement => {
  inputElement.addEventListener('change', evt => {
    onAdvancedSearchOptionsInputsChange();
  });
  inputElement.addEventListener('input', evt => {
    onAdvancedSearchOptionsInputsChange();
  });
});

advancedSearchOptionsDiv.getElementsByTagName("select").forEach(selectElement => {
  selectElement.addEventListener('change', evt => {
    onAdvancedSearchOptionsInputsChange();
  });
});

// Other sutff: form submission, navbar search form, hidden checkboxes etc.

var searchFormElement = document.getElementById('search_form');

searchFormElement.getElementsByClassName('bw-checkbox').forEach(checkbox => {
  const hiddenCheckbox = document.createElement('input');
  hiddenCheckbox.type = 'hidden';
  hiddenCheckbox.name = checkbox.name;
  checkbox.name = '';  // remove name attribute so checkbox is not submitted (the hidden input will be submitted instead)
  hiddenCheckbox.value = checkbox.checked ? '1' : '0';
  checkbox.addEventListener('change', evt => {  // Update hidden checkbox value when checkbox is changed
    hiddenCheckbox.value = checkbox.checked ? '1' : '0';
  });
  checkbox.parentNode.appendChild(hiddenCheckbox);
});

// Make the search select element submit the form when changed
var sortByElement = document.getElementById('id_sort_by');
if (sortByElement !== null){
  sortByElement.addEventListener('change', function() {
    searchFormElement.submit();
  })
}

// Make radio cluster elements submit the form when changed (also when cluster section is loaded asynchronously)
export const bindClusteringRadioButtonsSubmit = () => {
  document.getElementsByName('cid').forEach(radio => { 
    radio.addEventListener('change', (evt) => {
      setTimeout(() => {
        searchFormElement.submit();
      }, 100);  // Give it a little time to update the radio widget before submitting
    });
  })
}
bindClusteringRadioButtonsSubmit();
document.addEventListener('async_section_loaded', () => bindClusteringRadioButtonsSubmit());


document.body.addEventListener('keydown',  evt => {
  const ENTER_KEY = 13
  if(evt.keyCode === ENTER_KEY){
    // If ENTER key is pressed and search form is visible, trigger form submission
    if (searchFormIsVisible()){
      searchFormElement.submit();
    }
  }
})

var searchPageNavbarForm = document.getElementById('search-page-navbar-form');
if (searchPageNavbarForm !== null){
  searchPageNavbarForm.addEventListener('submit', function(evt){
    // Prevent default form submission
    if (evt.preventDefault) evt.preventDefault();
  
    // Copy input element contents to the main input element and do submission of the main form instead of the navbar one
    const searchInputBrowseNavbar = document.getElementById('search-input-browse-navbar');
    searchInputBrowse.value = searchInputBrowseNavbar.value;
    searchFormElement.submit();
  
    // It is also needed to return false to prevent default form submission
    return false;
  })
}

function onDocumentReady(){
  // Update the text of the button to toggle advanced search options panel
  updateToggleAdvancedSearchOptionsText();
  // Store values of advanced search filters so later we can check if they were modified
  initialAdvancedSearchInputValues = serializeAdvanceSearchOptionsInputsData();
}
document.addEventListener('DOMContentLoaded', onDocumentReady);