/* eslint-disable no-param-reassign */
import throttle from 'lodash.throttle'
import playerSettings from './settings'
import { formatAudioDuration } from './utils'
import { createIconElement } from '../../utils/icons'
import { createAudioElement, setProgressIndicator } from './audio-element'

/**
 *
 * @param {HTMLDivElement} parentNode
 * @param {HTMLAudioElement} audioElement
 */
const createProgressIndicator = (parentNode, audioElement) => {
  const progressIndicatorContainer = document.createElement('div')
  progressIndicatorContainer.className =
    'bw-player__progress-indicator-container'
  const progressIndicator = document.createElement('div')
  progressIndicator.className = 'bw-player__progress-indicator'
  progressIndicatorContainer.appendChild(progressIndicator)
  progressIndicatorContainer.addEventListener(
    'mousemove',
    throttle(evt => {
      const progressPercentage =
        evt.offsetX / progressIndicatorContainer.clientWidth
      setProgressIndicator(progressPercentage * 100, parentNode)
    }),
    50
  )
  progressIndicatorContainer.addEventListener('mouseleave', () => {
    setProgressIndicator(
      ((100 * audioElement.currentTime) / audioElement.duration) % 100,
      parentNode
    )
  })
  return progressIndicatorContainer
}

/**
 * @param {HTMLAudioElement} audioElement
 */
const createProgressBar = audioElement => {
  const progressBar = document.createElement('div')
  progressBar.className = 'bw-player__progress-bar'
  const progressBarIndicator = document.createElement('div')
  progressBarIndicator.className = 'bw-player__progress-bar-indicator'
  const progressBarIndicatorGhost = document.createElement('div')
  progressBarIndicatorGhost.className =
    'bw-player__progress-bar-indicator--ghost'
  const progressBarTime = document.createElement('div')
  progressBarTime.className = 'bw-player__progress-bar-indicator--time'
  progressBar.appendChild(progressBarIndicator)
  progressBar.appendChild(progressBarIndicatorGhost)
  progressBar.appendChild(progressBarTime)
  progressBar.addEventListener(
    'mousemove',
    throttle(evt => {
      progressBarIndicatorGhost.style.transform = `translateX(${evt.offsetX}px)`
      progressBarIndicatorGhost.style.opacity = 0.5
      progressBarTime.style.transform = `translateX(calc(${evt.offsetX}px - 50%))`
      progressBarTime.style.opacity = 1
      progressBarTime.innerHTML = formatAudioDuration(
        (audioElement.duration * evt.offsetX) / progressBar.clientWidth
      )
    }, 30)
  )
  progressBar.addEventListener('mouseleave', () => {
    progressBarIndicatorGhost.style.opacity = 0
    progressBarTime.style.opacity = 0
  })
  return progressBar
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {'small' | 'big'} playerSize
 * @param {bool} startWithSpectrum
 * @param {number} durationDataProperty
 */
const createProgressStatus = (audioElement, playerSize, startWithSpectrum, durationDataProperty) => {
  let { duration } = audioElement
  if ((duration === Infinity) || (isNaN(duration))){
    // Duration was not properly retrieved from audioElement. If given from data property, use that one.
    if (durationDataProperty !== undefined){
      duration = durationDataProperty
    }
  }
  const progressStatusContainer = document.createElement('div')
  progressStatusContainer.className = 'bw-player__progress-container'
  const progressBar = createProgressBar(audioElement)
  const progressStatus = document.createElement('div')
  progressStatus.className = 'bw-player__progress'
  const durationIndicator = document.createElement('span')
  durationIndicator.className = 'bw-total__sound_duration'
  const progressIndicator = document.createElement('span')
  progressIndicator.classList.add('hidden')
  if (playerSize === 'big') {
    progressStatusContainer.classList.add('bw-player__progress-container--big')
    progressStatus.classList.add('bw-player__progress--big')
    progressIndicator.classList.remove('hidden')
  } else {
    if (startWithSpectrum){
      progressStatusContainer.classList.add('bw-player__progress-container--inverted')
    }
  }
  durationIndicator.innerHTML = `${
    playerSettings.showRemainingTime ? '-' : ''
  }${formatAudioDuration(duration)}`
  progressIndicator.innerHTML = formatAudioDuration(0)
  progressStatus.appendChild(durationIndicator)
  progressStatus.appendChild(progressIndicator)
  if (playerSize === 'big') {
    progressStatusContainer.appendChild(progressBar)
  }
  progressStatusContainer.appendChild(progressStatus)
  return progressStatusContainer
}

/**
 *
 * @param {'play' | 'stop' | 'loop'} action
 */
const createControlButton = action => {
  const controlButton = document.createElement('button')
  controlButton.className = 'no-border-bottom-on-hover bw-player-control-btn'
  controlButton.appendChild(createIconElement(`bw-icon-${action}`))
  return controlButton
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {'small' | 'big'} playerSize
 */
const createPlayButton = (audioElement, playerSize) => {
  const playButton = createControlButton(
    playerSize === 'big' ? 'play-stroke' : 'play'
  )
  playButton.classList.add('bw-player__play-btn')
  playButton.addEventListener('click', (e) => {
    const isPlaying = !audioElement.paused
    if (isPlaying) {
      audioElement.pause()
    } else {
      audioElement.play()
    }
    e.stopPropagation()
  })
  return playButton
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {HTMLDivElement} parentNode
 */
const createStopButton = (audioElement, parentNode) => {
  const stopButton = createControlButton('stop')
  stopButton.addEventListener('click', (e) => {
    audioElement.pause()
    audioElement.currentTime = 0
    setProgressIndicator(0, parentNode)
    e.stopPropagation()
  })
  return stopButton
}

/**
 * @param {HTMLAudioElement} audioElement
 */
const createLoopButton = audioElement => {
  const loopButton = createControlButton('loop')
  loopButton.addEventListener('click', (e) => {
    const willLoop = !audioElement.loop
    if (willLoop) {
      loopButton.classList.add('text-red-important')
    } else {
      loopButton.classList.remove('text-red-important')
    }
    audioElement.loop = willLoop
    e.stopPropagation()
  })
  return loopButton
}

/**
 *
 * @param {HTMLImgElement} playerImgNode
 * @param {HTMLDivElement} parentNode
 * @param {'small' | 'big'} playerSize
 * @param {bool} startWithSpectrum
 */
const createSpectogramButton = (playerImgNode, parentNode, playerSize, startWithSpectrum) => {
  const spectogramButton = createControlButton('spectogram')
  const { spectrum, waveform } = parentNode.dataset
  if (startWithSpectrum){
    spectogramButton.classList.add('text-red-important');
  }
  spectogramButton.addEventListener('click', () => {
    const hasWaveform = playerImgNode.src.indexOf(waveform) > -1
    if (hasWaveform) {
      playerImgNode.src = spectrum
      spectogramButton.classList.add('text-red-important')
      spectogramButton.parentElement.classList.add('bw-player__controls-inverted');
      if (playerSize !== 'big'){
        spectogramButton.parentElement.parentElement.querySelector('.bw-player__progress-container').forEach((progressIndicator) => {
          progressIndicator.classList.add('bw-player__progress-inverted');
        });
      }
    } else {
      playerImgNode.src = waveform
      spectogramButton.classList.remove('text-red-important')
      spectogramButton.parentElement.classList.remove('bw-player__controls-inverted');
      if (playerSize !== 'big') {
        spectogramButton.parentElement.parentElement.querySelector('.bw-player__progress-container').forEach((progressIndicator) => {
          progressIndicator.classList.remove('bw-player__progress-inverted');
        });
      }
    }
  })
  return spectogramButton
}

const createRulerButton = () => {
  const rulerButton = createControlButton('ruler')
  return rulerButton
}

/**
 *
 * @param {HTMLDivElement} parentNode
 * @param {HTMLAudioElement} audioElement
 * @param {'small' | 'big'} playerSize
 */
const createPlayerImage = (parentNode, audioElement, playerSize) => {
  const imageContainer = document.createElement('div')
  imageContainer.className = 'bw-player__img-container'
  if (playerSize === 'big') {
    imageContainer.classList.add('bw-player__img-container--big')
  } else if (playerSize === 'minimal') {
    imageContainer.classList.add('bw-player__img-container--minimal')
  }
  if (playerSize !== 'minimal') {
    const startWithSpectrum = document.cookie.indexOf('preferSpectrogram=yes') > -1;
    const {waveform, spectrum, title, duration} = parentNode.dataset
    const playerImage = document.createElement('img')
    playerImage.className = 'bw-player__img'
    if (startWithSpectrum) {
      playerImage.src = spectrum
    } else {
      playerImage.src = waveform
    }
    playerImage.alt = title
    const progressIndicator = createProgressIndicator(parentNode, audioElement)
    imageContainer.appendChild(playerImage)
    imageContainer.appendChild(progressIndicator)
    const progressStatus = createProgressStatus(audioElement, playerSize, startWithSpectrum, parseFloat(duration, 10))
    imageContainer.appendChild(progressStatus)
    audioElement.addEventListener('loadedmetadata', () => {
      // If "loadedmetadata" event is received and valid duration value has been obtained, replace duration from data
      // property with "real" duration from loaded file
      if (audioElement.duration !== Infinity){
        progressStatus.getElementsByClassName('bw-total__sound_duration')[0].innerHTML = formatAudioDuration(audioElement.duration);
      }
    })
    imageContainer.addEventListener('click', evt => {
      const clickPosition = evt.offsetX
      const width = evt.target.clientWidth
      const positionRatio = clickPosition / width
      const time = audioElement.duration * positionRatio
      audioElement.currentTime = time
      if (audioElement.paused) {
        audioElement.play()
      }
      evt.stopPropagation()
    })
  }
  return imageContainer
}

/**
 *
 * @param {HTMLDivElement} parentNode
 * @param {HTMLImgElement} playerImgNode
 * @param {HTMLAudioElement} audioElement
 * @param {'small' | 'big'} playerSize
 */
const createPlayerControls = (parentNode, playerImgNode, audioElement, playerSize) => {
  const playerControls = document.createElement('div')
  playerControls.className = 'bw-player__controls stop-propagation'
  if (playerSize === 'big') {
    playerControls.classList.add('bw-player__controls--big')
  } else if (playerSize === 'minimal') {
    playerControls.classList.add('bw-player__controls--minimal')
  }

  let startWithSpectrum = false;
  if (playerImgNode !== undefined){  // Some players don't have playerImgNode (minimal)
    startWithSpectrum = playerImgNode.src.indexOf(parentNode.dataset.waveform) === -1;
  }
  if (startWithSpectrum){
    playerControls.classList.add('bw-player__controls-inverted');
  }

  const controls =
    playerSize === 'big'
      ? [createLoopButton(audioElement),
         createStopButton(audioElement, parentNode),
         createPlayButton(audioElement, playerSize),
         createSpectogramButton(playerImgNode, parentNode, playerSize, startWithSpectrum),
         createRulerButton()]
      : [createLoopButton(audioElement),
         createPlayButton(audioElement, playerSize)]
  controls.forEach(el => playerControls.appendChild(el))
  return playerControls
}

/**
 *
 * @param {HTMLDivElement} parentNode
 */
const createSetFavoriteButton = parentNode => {
  const getIsFavorite = () => parentNode.dataset.favorite === 'true'
  const favoriteButtonContainer = document.createElement('div')
  const favoriteButton = createControlButton('bookmark')
  const unfavoriteButton = createControlButton('bookmark-filled')
  favoriteButtonContainer.classList.add(
    'bw-player__favorite',
    'stop-propagation'
  )
  favoriteButtonContainer.appendChild(
    getIsFavorite() ? unfavoriteButton : favoriteButton
  )
  favoriteButtonContainer.addEventListener('click', (e) => {
    const isCurrentlyFavorite = getIsFavorite()
    favoriteButtonContainer.innerHTML = ''
    favoriteButtonContainer.appendChild(
      isCurrentlyFavorite ? favoriteButton : unfavoriteButton
    )
    parentNode.dataset.favorite = `${!isCurrentlyFavorite}`
    e.stopPropagation()
  })
  return favoriteButtonContainer
}

/**
 * @param {HTMLDivElement} parentNode
 */
const createPlayer = parentNode => {
  const playerSize = parentNode.dataset.size
  const showBookmarkButton = parentNode.dataset.bookmark === 'true'
  const audioElement = createAudioElement(parentNode)
  const playerImage = createPlayerImage(
    parentNode,
    audioElement,
    playerSize
  )
  const playerImgNode = playerImage.getElementsByTagName('img')[0]
  const controls = createPlayerControls(parentNode, playerImgNode, audioElement, playerSize)
  const bookmarkButton = createSetFavoriteButton(parentNode)

  parentNode.appendChild(playerImage)
  parentNode.appendChild(audioElement)
  playerImage.appendChild(controls)
  if (showBookmarkButton){
    playerImage.appendChild(bookmarkButton)
  }
}

export {createPlayer};
