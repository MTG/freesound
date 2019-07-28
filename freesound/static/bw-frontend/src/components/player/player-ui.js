/* eslint-disable no-param-reassign */
import playerSettings from './settings'
import { formatAudioDuration } from './utils'
import { createIconElement } from '../../utils/icons'
import { createAudioElement, setProgressIndicator } from './audio-element'

const createProgressIndicator = () => {
  const progressIndicator = document.createElement('div')
  progressIndicator.className = 'bw-player__progress-indicator'
  return progressIndicator
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {'small' | 'big'} playerSize
 */
const createProgressStatus = (audioElement, playerSize) => {
  const { duration } = audioElement
  const progressStatus = document.createElement('div')
  progressStatus.className = 'bw-player__progress'
  const durationIndicator = document.createElement('span')
  const progressIndicator = document.createElement('span')
  progressIndicator.classList.add('hidden')
  if (playerSize === 'big') {
    progressStatus.classList.add('bw-player__progress--big')
    progressIndicator.classList.remove('hidden')
  }
  durationIndicator.innerHTML = `${
    playerSettings.showRemainingTime ? '-' : ''
  }${formatAudioDuration(duration)}`
  progressIndicator.innerHTML = formatAudioDuration(0)
  progressStatus.appendChild(durationIndicator)
  progressStatus.appendChild(progressIndicator)
  return progressStatus
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
  const progressIndicator = createProgressIndicator()
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

  parentNode.appendChild(waveformImage)
  parentNode.appendChild(audioElement)
  waveformImage.appendChild(controls)
}

const setupPlayers = () => {
  const players = [...document.getElementsByClassName('bw-player')]
  players.forEach(createPlayer)
}

setupPlayers()
