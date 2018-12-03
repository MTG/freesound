import throttle from 'lodash.throttle';

const navbar = document.getElementsByClassName('bw-nav')[0];

// call with once() to avoid adding the same event listener multiple times
const addScrollEventListener = () => {
  // min interval (in ms) between consecutive calls of scroll checking function
  const SCROLL_CHECK_TIMER = 100;
  const checkShouldShowNavbarShadow = throttle(() => {
    const scrollingPosition = window.pageYOffset;
    const shouldShowShadow = scrollingPosition > 30;
    const isShowingShadow = navbar.classList.contains('bw-nav--scrolled');
    if (shouldShowShadow !== isShowingShadow) {
      navbar.classList.toggle('bw-nav--scrolled');
    }
  }, SCROLL_CHECK_TIMER);

  window.addEventListener('scroll', checkShouldShowNavbarShadow);
};

// finally call the 'once' functions
addScrollEventListener();

export default navbar;
