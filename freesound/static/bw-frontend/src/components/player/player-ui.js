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
        evt.layerX / progressIndicatorContainer.clientWidth
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
      progressBarIndicatorGhost.style.transform = `translateX(${evt.layerX}px)`
      progressBarIndicatorGhost.style.opacity = 0.5
      progressBarTime.style.transform = `translateX(calc(${evt.layerX}px - 50%))`
      progressBarTime.style.opacity = 1
      progressBarTime.innerHTML = formatAudioDuration(
        (audioElement.duration * evt.layerX) / progressBar.clientWidth
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
 */
const createProgressStatus = (audioElement, playerSize) => {
  const { duration } = audioElement
  const progressStatusContainer = document.createElement('div')
  progressStatusContainer.className = 'bw-player__progress-container'
  const progressBar = createProgressBar(audioElement)
  const progressStatus = document.createElement('div')
  progressStatus.className = 'bw-player__progress'
  const durationIndicator = document.createElement('span')
  const progressIndicator = document.createElement('span')
  progressIndicator.classList.add('hidden')
  if (playerSize === 'big') {
    progressStatusContainer.classList.add('bw-player__progress-container--big')
    progressStatus.classList.add('bw-player__progress--big')
    progressIndicator.classList.remove('hidden')
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
  playButton.addEventListener('click', () => {
    const isPlaying = !audioElement.paused
    if (isPlaying) {
      audioElement.pause()
    } else {
      audioElement.play()
    }
  })
  return playButton
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {HTMLDivElement} parentNode
 */
const createStopButton = (audioElement, parentNode) => {
  const stopButton = createControlButton('stop')
  stopButton.addEventListener('click', () => {
    audioElement.pause()
    audioElement.currentTime = 0
    setProgressIndicator(0, parentNode)
  })
  return stopButton
}

/**
 * @param {HTMLAudioElement} audioElement
 */
const createLoopButton = audioElement => {
  const loopButton = createControlButton('loop')
  loopButton.addEventListener('click', () => {
    const willLoop = !audioElement.loop
    if (willLoop) {
      loopButton.classList.add('text-red')
    } else {
      loopButton.classList.remove('text-red')
    }
    audioElement.loop = willLoop
  })
  return loopButton
}

const createSpectogramButton = () => {
  const spectogramButton = createControlButton('spectogram')
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
const createWaveformImage = (parentNode, audioElement, playerSize) => {
  const imageContainer = document.createElement('div')
  imageContainer.className = 'bw-player__img-container'
  if (playerSize === 'big') {
    imageContainer.classList.add('bw-player__img-container--big')
  }
  const { waveform, title } = parentNode.dataset
  const waveformImage = document.createElement('img')
  waveformImage.className = 'bw-player__img'
  waveformImage.src = waveform
  waveformImage.alt = title
  const progressIndicator = createProgressIndicator(parentNode, audioElement)
  imageContainer.appendChild(waveformImage)
  imageContainer.appendChild(progressIndicator)
  audioElement.addEventListener('loadedmetadata', () => {
    const progressStatus = createProgressStatus(audioElement, playerSize)
    imageContainer.appendChild(progressStatus)
  })
  imageContainer.addEventListener('click', evt => {
    const clickPosition = evt.layerX
    const width = evt.target.clientWidth
    const positionRatio = clickPosition / width
    const time = audioElement.duration * positionRatio
    audioElement.currentTime = time
    if (audioElement.paused) {
      audioElement.play()
    }
  })
  return imageContainer
}

/**
 *
 * @param {HTMLDivElement} parentNode
 * @param {HTMLAudioElement} audioElement
 * @param {'small' | 'big'} playerSize
 */
const createPlayerControls = (parentNode, audioElement, playerSize) => {
  const playerControls = document.createElement('div')
  playerControls.className = 'bw-player__controls stop-propagation'
  if (playerSize === 'big') {
    playerControls.classList.add('bw-player__controls--big')
  }
  const playButton = createPlayButton(audioElement, playerSize)
  const stopButton = createStopButton(audioElement, parentNode)
  const loopButton = createLoopButton(audioElement)
  const spectogramButton = createSpectogramButton()
  const rulerButton = createRulerButton()
  const controls =
    playerSize === 'big'
      ? [loopButton, stopButton, playButton, spectogramButton, rulerButton]
      : [loopButton, playButton]
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
  favoriteButtonContainer.addEventListener('click', () => {
    const isCurrentlyFavorite = getIsFavorite()
    favoriteButtonContainer.innerHTML = ''
    favoriteButtonContainer.appendChild(
      isCurrentlyFavorite ? favoriteButton : unfavoriteButton
    )
    parentNode.dataset.favorite = `${!isCurrentlyFavorite}`
  })
  return favoriteButtonContainer
}

/**
 * @param {HTMLDivElement} parentNode
 */
const createPlayer = parentNode => {
  const playerSize = parentNode.dataset.size
  const audioElement = createAudioElement(parentNode)
  const waveformImage = createWaveformImage(
    parentNode,
    audioElement,
    playerSize
  )
  const controls = createPlayerControls(parentNode, audioElement, playerSize)
  const bookmarkButton = createSetFavoriteButton(parentNode)

  parentNode.appendChild(waveformImage)
  parentNode.appendChild(audioElement)
  waveformImage.appendChild(controls)
  waveformImage.appendChild(bookmarkButton)
}

const setupPlayers = () => {
  const players = [...document.getElementsByClassName('bw-player')]
  players.forEach(createPlayer)
}

setupPlayers()
