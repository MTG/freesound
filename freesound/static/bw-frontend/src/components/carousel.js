import { createIconElement } from '../utils/icons'
import { addHorizontalSwipeListener } from '../utils/swipeDetector'


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
  
  let totalPages = 0;
  if (carousel.dataset.carouselType === "adaptive"){
    // Adaptive carousels will count the number of pages depending on the size of the child elements instead of separating 
    // them in rows. In this way we can have players with adapted size depending on overall screen size and carousels will 
    // adapt as well
    const rowWithElements = carouselContainer.children[0];
    const firstElement = rowWithElements.children[0];
    const elementsPerPage = Math.round(rowWithElements.offsetWidth / firstElement.offsetWidth);
    totalPages = Math.round(rowWithElements.childElementCount / elementsPerPage);
  } else {
    totalPages = carouselContainer.childElementCount
  }
  
  const hasDots = carouselContainer.classList.contains('with-dots') && totalPages > 1;
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
    if (totalPages > 1){
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
  if (totalPages > 1){
    rightArrow.classList.add('carousel-right')
  } else {
    rightArrow.classList.add('carousel-right', 'carousel-nav-hidden')
  }
  carousel.append(leftArrow)
  carousel.append(rightArrow)
  rightArrow.addEventListener('click', () => {
    clearAutoRotateTimer() // When manually selection one page, stop auto rotating
    setPage(currentPage + 1)
  })
  leftArrow.addEventListener('click', () => {
    clearAutoRotateTimer() // When manually selection one page, stop auto rotating
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
        clearAutoRotateTimer() // When manually selection one page, stop auto rotating
        setPage(i)
      })
    }
    carousel.append(dotIconsParent)
  }
  setPage(0)

  if (carousel.dataset.carouselAutoRotateSeconds !== undefined){
    const seconds = parseInt(carousel.dataset.carouselAutoRotateSeconds, 10);
    carousel.autoRotateInterval = setInterval(() => {
      setPage((currentPage + 1) % totalPages);
    }, seconds * 1000);
  }

  const clearAutoRotateTimer = () => {
    if (carousel.autoRotateInterval !== null){
      window.clearInterval(carousel.autoRotateInterval);
    } 
  }

  addHorizontalSwipeListener(carousel, (direction) => {
    clearAutoRotateTimer() // When manually selection one page, stop auto rotating
    if (direction) {
      setPage(currentPage - 1);
    } else {
      setPage(currentPage + 1);
    }
  })
})

