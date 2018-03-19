import throttle from 'lodash.throttle';
import navbar from '../components/navbar';

const heroSearch = document.getElementsByClassName('bw-front__hero-search')[0];

const SCROLL_CHECK_TIMER = 100; // min interval (in ms) between consecutive calls of scroll checking function
const checkShouldShowSearchInNavbar = throttle(() => {
  const heroRect = heroSearch.getBoundingClientRect();
  // not all browsers support clientRect.height
  const heroSearchPosition = heroRect.height ? heroRect.y + heroRect.height : heroRect.y;
  const shouldShowSearchBar = heroSearchPosition < 80;
  const isShowingSearchBar = !navbar.classList.contains('bw-nav--expanded');
  if (shouldShowSearchBar !== isShowingSearchBar) {
    navbar.classList.toggle('bw-nav--expanded');
  }
}, SCROLL_CHECK_TIMER);

window.addEventListener('scroll', checkShouldShowSearchInNavbar);
