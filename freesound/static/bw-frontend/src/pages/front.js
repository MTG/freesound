import './page-polyfills'
import throttle from 'lodash.throttle'
import navbar from '../components/navbar'
import { addTypeAheadFeatures } from '../components/typeahead'
import wait from '../utils/wait'

const heroSearch = document.getElementsByClassName('bw-front__hero-search')[0]

const input = document.getElementById('search-sounds')

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

const fetchSuggestions = async query => {
  const fakeSuggestions = [
    { id: 0, label: '<p>first suggestion</p>', value: 'first suggestion' },
    { id: 1, label: '<p>second suggestion</p>', value: 'second suggestion' },
    { id: 2, label: '<p>third suggestion</p>', value: 'third suggestion' },
    { id: 3, label: '<p>fourth suggestion</p>', value: 'fourth suggestion' },
    { id: 4, label: '<p>fifth suggestion</p>', value: 'fifth suggestion' },
    { id: 5, label: '<p>sixth suggestion</p>', value: 'sixth suggestion' },
    { id: 6, label: '<p>seventh suggestion</p>', value: 'seventh suggestion' },
    { id: 7, label: '<p>eight suggestion</p>', value: 'eight suggestion' },
  ]
  // wait 1s just to pretend we're actually calling a server
  await wait(1000)
  return fakeSuggestions
}

addTypeAheadFeatures(input, fetchSuggestions)
