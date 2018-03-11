import throttle from 'lodash.throttle';
import { getIcon } from '../utils/icons';
import once from '../utils/once';

const navbar = document.getElementsByClassName('bw-nav')[0];
const navbarMenusAnchors = [...document.getElementsByClassName('bw-nav__menu')];

// call once() to avoid adding ellipsis icons multiple times
const addEllipsisIconToMenusOnce = once('navbar-ellipsis-icon', () => {
  const ellipsisSvg = getIcon('ellipsis');
  navbarMenusAnchors.forEach(el => el.appendChild(ellipsisSvg));
});

// call with once() to avoid adding the same event listener multiple times
const addScrollEventListenerOnce = once('navbar-scroll-listeners', () => {
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
});

// finally call the 'once' functions
addEllipsisIconToMenusOnce();
addScrollEventListenerOnce();

export default navbar;
