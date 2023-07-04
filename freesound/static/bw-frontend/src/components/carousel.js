import { createIconElement } from '../utils/icons'
import { addHorizontalSwipeListener } from '../utils/swipeDetector'

const autoprefixedTransformProperties = [
  'WebkitTransform',
  'msTransform',
  'MozTransform',
  'transform',
]

const initializeCarousels = (parentContainer) => {
  let carouselContainers;
  if (parentContainer === undefined){
    carouselContainers = [...document.getElementsByClassName('bw-carousel-container')]
  } else {
    carouselContainers = [...parentContainer.getElementsByClassName('bw-carousel-container')]
  }

  carouselContainers.forEach(carouselContainer => {
    const carousel = [
      ...carouselContainer.getElementsByClassName('bw-carousel'),
    ][0]
    if (!carousel) return
    
    let totalPages = 0;
    if (carouselContainer.dataset.carouselType === "adaptive"){
      // Adaptive carousels will count the number of pages depending on the size of the child elements instead of separating 
      // them in rows. In this way we can have players with adapted size depending on overall screen size and carousels will 
      // adapt as well
      const rowWithElements = carousel.children[0];
      const firstElement = rowWithElements.children[0];
      const elementsPerPage = Math.round(rowWithElements.offsetWidth / firstElement.offsetWidth);
      totalPages = Math.round(rowWithElements.childElementCount / elementsPerPage);
    } else {
      totalPages = carousel.childElementCount
    }
    
    const hasDots = carousel.classList.contains('with-dots') && totalPages > 1;
    let currentPage = 0
    const leftArrow = document.createElement('div')
    const rightArrow = document.createElement('div')
    const transitionWrapper = carouselContainer.getElementsByClassName('bw-transition-wrapper')[0]; // Might be undefined
    const setPage = desiredPage => {
      if (desiredPage < 0 || desiredPage >= totalPages) return
      if (transitionWrapper !== undefined) {
        // While transitining, add overflow hidden to the transition wrapper div so no "artifacts" are created because the negative margin to align the carousels
        transitionWrapper.classList.add('overflow-hidden');
        setTimeout( () => {transitionWrapper.classList.remove('overflow-hidden');}, 300)
      }
      currentPage = desiredPage
      const desiredTranslation = (100 / totalPages) * desiredPage
      autoprefixedTransformProperties.forEach(transform => {
        carousel.style[transform] = `translateX(-${desiredTranslation}%)`
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
          const dots = [...carouselContainer.getElementsByClassName('bw-icon-atom')]
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
    carousel.style.width = width
    const children = [...carousel.children]
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
    carouselContainer.append(leftArrow)
    carouselContainer.append(rightArrow)
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
      if (carousel.className.match(/dots-distance-\d/)) {
        const distance = carousel.className.match(
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
      carouselContainer.append(dotIconsParent)
    }
    setPage(0)

    if (carouselContainer.dataset.carouselAutoRotateSeconds !== undefined){
      const seconds = parseInt(carouselContainer.dataset.carouselAutoRotateSeconds, 10);
      carouselContainer.autoRotateInterval = setInterval(() => {
        setPage((currentPage + 1) % totalPages);
      }, seconds * 1000);
    }

    const clearAutoRotateTimer = () => {
      if (carouselContainer.autoRotateInterval !== null){
        window.clearInterval(carouselContainer.autoRotateInterval);
      } 
    }

    addHorizontalSwipeListener(carouselContainer, (direction) => {
      clearAutoRotateTimer() // When manually selection one page, stop auto rotating
      if (direction) {
        setPage(currentPage - 1);
      } else {
        setPage(currentPage + 1);
      }
    })
  })
}

initializeCarousels();

export {initializeCarousels};