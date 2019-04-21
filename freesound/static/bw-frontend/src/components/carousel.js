import { createIconElement } from '../utils/icons'

const carousels = [...document.getElementsByClassName('bw-carousel-container')]

const autoprefixedTransformProperties = [
  'WebkitTransform',
  'msTransform',
  'MozTransform',
  'transform',
]

carousels.forEach(carousel => {
  const carouselContainer = [
    ...carousel.getElementsByClassName('bw-carousel'),
  ][0]
  if (!carouselContainer) return
  const totalPages = carouselContainer.childElementCount
  let currentPage = 0
  const setPage = desiredPage => {
    if (desiredPage < 0 || desiredPage >= totalPages) return
    currentPage = desiredPage
    const desiredTranslation = (100 / totalPages) * desiredPage
    autoprefixedTransformProperties.forEach(transform => {
      carouselContainer.style[transform] = `translateX(-${desiredTranslation}%)`
    })
    if (currentPage === 0) {
      leftArrow.classList.add('carousel-nav-hidden')
      rightArrow.classList.remove('carousel-nav-hidden')
    } else if (currentPage === totalPages - 1) {
      leftArrow.classList.remove('carousel-nav-hidden')
      rightArrow.classList.add('carousel-nav-hidden')
    } else {
      leftArrow.classList.remove('carousel-nav-hidden')
      rightArrow.classList.remove('carousel-nav-hidden')
    }
  }
  const width = `${totalPages * 100}%`
  carouselContainer.style.width = width
  const children = [...carouselContainer.children]
  children.forEach(child => {
    child.style.width = `${100 / totalPages}%`
  })

  const leftArrow = document.createElement('div')
  const rightArrow = document.createElement('div')
  const navigationArrows = [leftArrow, rightArrow]
  navigationArrows.forEach(element => {
    element.classList.add('bw-carousel-icon')
    element.append(createIconElement('bw-icon-arrow'))
  })
  leftArrow.classList.add('carousel-left', 'carousel-nav-hidden')
  rightArrow.classList.add('carousel-right')
  carousel.append(leftArrow)
  carousel.append(rightArrow)
  rightArrow.addEventListener('click', () => {
    setPage(currentPage + 1)
  })
  leftArrow.addEventListener('click', () => {
    setPage(currentPage - 1)
  })
})
