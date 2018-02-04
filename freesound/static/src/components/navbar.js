import { getIcon } from '../utils/icons';

const navbarMenusAnchors = [...document.getElementsByClassName('bw-nav__menu')];

const ellipsisSvg = getIcon('ellipsis');

navbarMenusAnchors.forEach(el => {
  el.appendChild(ellipsisSvg);
});
