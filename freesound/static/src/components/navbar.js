import throttle from 'lodash.throttle';
import { getIcon } from '../utils/icons';

const navbar = document.getElementsByClassName('bw-nav')[0];
const navbarMenusAnchors = [...document.getElementsByClassName('bw-nav__menu')];

const ellipsisSvg = getIcon('ellipsis');

navbarMenusAnchors.forEach(el => {
  const menuChildren = [...el.childNodes];
  const hasAlreadyEllipsisIcon = menuChildren.some(child => child.tagName === 'svg');
  if (!hasAlreadyEllipsisIcon) {
    el.appendChild(ellipsisSvg);
  }
});

const SCROLL_CHECK_TIMER = 100; // min interval (in ms) between consecutive calls of scroll checking function
const checkShouldShowNavbarShadow = throttle(() => {
  const scrollingPosition = window.pageYOffset;
  const shouldShowShadow = scrollingPosition > 30;
  const isShowingShadow = navbar.classList.contains('bw-nav--scrolled');
  if (shouldShowShadow !== isShowingShadow) {
    navbar.classList.toggle('bw-nav--scrolled');
  }
}, SCROLL_CHECK_TIMER);

window.addEventListener('scroll', checkShouldShowNavbarShadow);

export default navbar;
