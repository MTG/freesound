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

// Navbar search input box behaviour (should only appear when searchInputBrowse is not visible)
const searchFormIsVisible = () => {
  const heroRect = searchInputBrowse.getBoundingClientRect()
  // not all browsers support clientRect.height
  const heroSearchPosition = heroRect.height
    ? heroRect.y + heroRect.height
    : heroRect.y
  return heroSearchPosition >= 80;
}

const SCROLL_CHECK_TIMER = 100 // min interval (in ms) between consecutive calls of scroll checking function
const checkShouldShowSearchInNavbar = throttle(() => {
  const shouldShowSearchBar = !searchFormIsVisible();
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
var advanced_search_hidden_field = document.getElementById('advanced_search_hidden');
var toggle_advanced_search_options_element = document.getElementById('toggle_advanced_search_options');
var filter_query_element = document.getElementById('filter_query');
var filter_duration_min_element = document.getElementById('filter_duration_min');
var filter_duration_max_element = document.getElementById('filter_duration_max');
var filter_is_geotagged_element = document.getElementById('filter_is_geotagged');
var sort_by_element = document.getElementById('sort-by');
var grouping_geotagged_element  = document.getElementById('grouping_geotagged');
var only_sounds_with_pack_element  = document.getElementById('only_sounds_with_pack');

function updateToggleAdvancedSearchOptionsText()
{
  if (advanced_search_hidden_field.value === "1"){
    toggle_advanced_search_options_element.innerHTML = 'Hide advanced search options';
  } else {
    toggle_advanced_search_options_element.innerHTML = 'Show advanced search options';
  }
}

function showAdvancedSearchOptions()
{
  advanced_search_hidden_field.value = "1";
  advanced_search_options_div.style.display = 'block';
  updateToggleAdvancedSearchOptionsText();
}

function hideAdvancedSearchOptions()
{
  advanced_search_hidden_field.value = "0";
  advanced_search_options_div.style.display = 'none';
  updateToggleAdvancedSearchOptionsText();
}

function toggleAdvancedSearchOptions(){
  if (advanced_search_hidden_field.value === "1"){
    hideAdvancedSearchOptions();
  } else {
    showAdvancedSearchOptions();
  }
}

toggle_advanced_search_options_element.addEventListener('click', toggleAdvancedSearchOptions);

function set_hidden_grouping_value(){
  var element = document.getElementById('grouping_geotagged');
  var hiddenElement = document.getElementById('grouping_geotagged_hidden');
  if (element.checked) {
    hiddenElement.value = "1";
  } else {
    hiddenElement.value = "";
  }
}

function set_hidden_only_sounds_with_pack_value(){
  var element = document.getElementById('only_sounds_with_pack');
  var hiddenElement = document.getElementById('only_sounds_with_pack_hidden');
  if (element.checked) {
    hiddenElement.value = "1";
  } else {
    hiddenElement.value = "";
  }
}

// Return the value of a filter given its name
// If filter has a range, optional "range" parameter must be set to "min or "max"
function getFilterValue(name, range)
{
  if (!range) { range = "min"}

  var filter_query_element = document.getElementById('filter_query');
  var value = filter_query_element.value;
  var position_value = value.search(name) + (name + ":").length
  if (value.search((name + ":")) !== -1)
  {
    if (value[position_value] === "[") // Is range (with spaces)
    {
      var aux_value = value.substring(position_value + 1)
      var position_end = position_value + aux_value.search("]") + 2

      var range_string = value.substring(position_value + 1, position_end -1) // Without [ ]
      var parts = range_string.split(" ")
      if (range === "min"){
        return parts[0]
      } else if (range === "max") {
        return parts[2]
      }
    }
    else if (value[position_value] === "\"") // Is string (with spaces)
    {
      aux_value = value.substring(position_value + 1)
      position_end = position_value + aux_value.search("\"") + 2
      return value.substring(position_value, position_end)

    }
    else // Is number or normal text (without spaces)
    {
      aux_value = value.substring(position_value + 1)
      if (aux_value.search(" ") !== -1){
        position_end = position_value + aux_value.search(" ") + 1
      } else {
        position_end = value.length
      }
      return value.substring(position_value, position_end)
    }
  } else {
    return ""
  }
}

// Remove a filter given the full tag ex: type:aiff, pack:"pack name"
function removeFilter(tag)
{
  var filter_query_element = document.getElementById('filter_query');
  var value = filter_query_element.value;
  var cleaned = value.replace(tag + " ", "").replace(tag, "").trim();
  filter_query_element.value = cleaned;
}

function onDocumentReady(){
  // Fill advanced search fields that were passed through the f parameter
  // Duration

  if (getFilterValue("duration","min") === ""){
    filter_duration_min_element.value = "0";
  } else {
    filter_duration_min_element.value = getFilterValue("duration","min");
  }

  if (getFilterValue("duration","max") === ""){
    filter_duration_max_element.value = "*";
  } else {
    filter_duration_max_element.value = getFilterValue("duration","max");
  }

  // Geotagged
  if (getFilterValue("is_geotagged") === "1"){
    filter_is_geotagged_element.checked = true;
  }

  // Update the text of the button to toggle advanced search options panel
  updateToggleAdvancedSearchOptionsText();
}

document.addEventListener('DOMContentLoaded', onDocumentReady);

function addAdvancedSearchOptionsFilters()
{
  // Remove previously existing advanced options filters (will be replaced by current ones)
  var existing_duration_filter = "duration:[" + getFilterValue("duration","min") + " TO " + getFilterValue("duration","max") + "]";
  removeFilter(existing_duration_filter);
  removeFilter("is_geotagged:1");

  // if advanced options is activated add all updated filters
  if (advanced_search_hidden_field.value === "1")
  {
    // Create and add new filter with all the advanced options
    var filter = "";

    // Duration filter
    var duration_min = parseFloat(filter_duration_min_element.value);
    var duration_max = parseFloat(filter_duration_max_element.value);

    if ((duration_min >= 0.0) || (duration_max >= 0.0)) {
      var duration_filter = "";
      if ((duration_min >= 0.0) && (duration_max >= 0.0)) {  // Both min and max have been set
        if (duration_max < duration_min) {
          // interchange values if duration_min > duration_max
          var duration_aux = duration_min;
          duration_min = duration_max;
          duration_max = duration_aux;
        }
        duration_filter = "duration:[" + duration_min + " TO " + duration_max + "]";
      } else if (duration_min >= 0.0) {  // Only minimum has been set
        duration_filter = "duration:[" + duration_min + " TO *]";
      } else if (duration_max >= 0.0) {  // Only maximum has been set
        duration_filter = "duration:[* TO " + duration_max + "]";
      }
      filter = filter + duration_filter;
    }

    // Is geotagged filter
    if (filter_is_geotagged_element.checked){
      if (filter !== ""){
        filter = filter + " ";
      }
      filter = filter + "is_geotagged:1";
    }

    // Update general filter with the advanced options filter
    var value = filter_query_element.value;
    if (value !== ""){
      filter_query_element.value = value + " " + filter;
    } else {
      filter_query_element.value = filter;
    }
  }
}

search_form_element.addEventListener('submit', function() {
  addAdvancedSearchOptionsFilters();
})

sort_by_element.addEventListener('change', function() {
  addAdvancedSearchOptionsFilters();
  search_form_element.submit();
})

grouping_geotagged_element.addEventListener('change', function() {
  set_hidden_grouping_value();
})

only_sounds_with_pack_element.addEventListener('change', function() {
  set_hidden_only_sounds_with_pack_value();
})

document.body.addEventListener('keydown',  evt => {
  const ENTER_KEY = 13
  if(evt.keyCode === ENTER_KEY){
    // If ENTER key is pressed and search form is visible, trigger form submission
    if (searchFormIsVisible()){
      addAdvancedSearchOptionsFilters();
      search_form_element.submit();
    }
  }
})

search_page_navbar_form.addEventListener('submit', function(evt){
  // Prevent default form submission
  if (evt.preventDefault) evt.preventDefault();

  // Copy input element contents to the main input element and do submission of the main form instead of the navbar one
  const searchInputBrowseNavbar = document.getElementById('search-input-browse-navbar');
  searchInputBrowse.value = searchInputBrowseNavbar.value;
  addAdvancedSearchOptionsFilters();
  search_form_element.submit();

  // It is also needed to return false to prevent default form submission
  return false;
})
