import throttle from 'lodash.throttle';

const navbar = document.getElementsByClassName('bw-nav')[0];

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

addScrollEventListener();

export default navbar;
