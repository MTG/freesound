// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const stopPropagations = [...document.querySelectorAll('.stop-propagation')]

stopPropagations.forEach(el => {
  el.addEventListener('click', evt => evt.stopPropagation())
})

// @license-end
