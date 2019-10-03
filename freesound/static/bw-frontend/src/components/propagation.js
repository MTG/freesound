const stopPropagations = [...document.querySelectorAll('.stop-propagation')]

stopPropagations.forEach(el => {
  el.addEventListener('click', evt => evt.stopPropagation())
})
