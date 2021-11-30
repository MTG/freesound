import './page-polyfills'
import throttle from 'lodash.throttle'
import navbar from '../components/navbar'
import { addTypeAheadFeatures } from '../components/typeahead'
import wait from '../utils/wait'

// Main search input box behaviour
const input = document.getElementById('search-sounds')
const querySuggestionsURL = input.dataset.querySuggestionsUrl

const fetchSuggestions = async query => {
  let response = await fetch(`${querySuggestionsURL}?q=${input.value}`)
  let data = await response.json()
  const suggestions = data.suggestions
  return suggestions
}

addTypeAheadFeatures(input, fetchSuggestions)

// Navbar search input box behaviour  (shouold only appear when heroSearch is not visible)
const heroSearch = document.getElementsByClassName('bw-front__hero-search')[0]
const SCROLL_CHECK_TIMER = 100 // min interval (in ms) between consecutive calls of scroll checking function
const checkShouldShowSearchInNavbar = throttle(() => {
  const heroRect = heroSearch.getBoundingClientRect()
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

const randomSoundDetailsToggleLink = document.getElementById('randomSoundDetailsToggleLink');
const randomSoundDetails = document.getElementById('randomSoundDetails');

randomSoundDetailsToggleLink.addEventListener('click', () => {
  if (randomSoundDetails.classList.contains('display-none')){
      randomSoundDetails.classList.remove('display-none');
      randomSoundDetailsToggleLink.innerText = "Hide details";
  } else{
      randomSoundDetails.classList.add('display-none');
      randomSoundDetailsToggleLink.innerText = "Reveal details";
  }
});