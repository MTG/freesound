import { getIcon } from '../utils/icons'

const navbarMenusAnchors = [...document.getElementsByClassName('bw-nav__menu')];
console.log(document.body)

const ellipsisSvg = getIcon('ellipsis')

navbarMenusAnchors.forEach(el => {
  el.appendChild(ellipsisSvg);
});
