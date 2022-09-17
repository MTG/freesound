// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import { createIconElement } from '../utils/icons'
import {  isTouchEnabledDevice } from './player/utils'

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
  const hasDots = carouselContainer.classList.contains('with-dots')
  let currentPage = 0
  const leftArrow = document.createElement('div')
  const rightArrow = document.createElement('div')
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
    if (hasDots) {
      const dotsParent = carouselContainer.parentNode.parentNode.getElementsByClassName(
        'carousel__dot-icons'
      )[0]
      const dots = [...dotsParent.getElementsByClassName('bw-icon-atom')]
      dots.forEach((dot, dotIndex) => {
        if (dotIndex === desiredPage) {
          dot.classList.add('active-point')
        } else {
          dot.classList.remove('active-point')
        }
      })
    }
  }
  const width = `${totalPages * 100}%`
  carouselContainer.style.width = width
  const children = [...carouselContainer.children]
  children.forEach(child => {
    // eslint-disable-next-line no-param-reassign
    child.style.width = `${100 / totalPages}%`
  })

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
  if (hasDots) {
    const dotIconsParent = document.createElement('div')
    dotIconsParent.classList.add('carousel__dot-icons')
    if (carouselContainer.className.match(/dots-distance-\d/)) {
      const distance = carouselContainer.className.match(
        /dots-distance-(\d)/
      )[1]
      dotIconsParent.classList.add(`dots-distance-${distance}`)
    }
    for (let i = 0; i < totalPages; i += 1) {
      const dotIcon = createIconElement('bw-icon-atom')
      dotIconsParent.append(dotIcon)
      dotIcon.addEventListener('click', () => {
        setPage(i)
      })
    }
    if (isTouchEnabledDevice()) {
      // For touch-enabled devices, make dots always visible to suggest carousel interaction
      dotIconsParent.classList.add('opacity-080')
    }
    carousel.append(dotIconsParent)
  }
  setPage(0)
})

// @license-end
