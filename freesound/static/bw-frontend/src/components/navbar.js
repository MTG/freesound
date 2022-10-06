// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

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

// @license-end
