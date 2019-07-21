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
 */
const createProgressStatus = audioElement => {
  const { duration } = audioElement
  const progressStatus = document.createElement('div')
  progressStatus.className = 'bw-player__progress'
  progressStatus.innerHTML = `${
    playerSettings.showRemainingTime ? '-' : ''
  }${formatAudioDuration(duration)}`
  return progressStatus
}

/**
 *
 * @param {'play' | 'stop' | 'loop'} action
 */
const createControlButton = action => {
  const controlButton = document.createElement('button')
  controlButton.className = 'no-border-bottom-on-hover'
  controlButton.appendChild(createIconElement(`bw-icon-${action}`))
  return controlButton
}

/**
 * @param {HTMLAudioElement} audioElement
 */
const createPlayButton = audioElement => {
  const playButton = createControlButton('play')
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

/**
 * @param {HTMLAudioElement} audioElement
 */
const createPlayerControls = (audioElement, parentNode) => {
  const playerControls = document.createElement('div')
  playerControls.className = 'bw-player__controls'
  const playButton = createPlayButton(audioElement)
  const stopButton = createStopButton(audioElement, parentNode)
  const loopButton = createLoopButton(audioElement)
  const controls = [playButton, stopButton, loopButton]
  controls.forEach(el => playerControls.appendChild(el))
  return playerControls
}

const createWaveformImage = (parentNode, audioElement) => {
  const imageContainer = document.createElement('div')
  imageContainer.className = 'bw-player__img-container'
  const { waveform, title } = parentNode.dataset
  const waveformImage = document.createElement('img')
  waveformImage.className = 'bw-player__img'
  waveformImage.src = waveform
  waveformImage.alt = title
  const progressIndicator = createProgressIndicator()
  const playerControls = createPlayerControls(audioElement, parentNode)
  imageContainer.appendChild(waveformImage)
  imageContainer.appendChild(progressIndicator)
  imageContainer.appendChild(playerControls)
  audioElement.addEventListener('loadedmetadata', () => {
    const progressStatus = createProgressStatus(audioElement)
    imageContainer.appendChild(progressStatus)
  })
  return imageContainer
}

/**
 * @param {HTMLDivElement} parentNode
 */
const createPlayer = parentNode => {
  const audioElement = createAudioElement(parentNode)
  const waveformImage = createWaveformImage(parentNode, audioElement)

  parentNode.appendChild(waveformImage)
  parentNode.appendChild(audioElement)
}

const setupPlayers = () => {
  const players = [...document.getElementsByClassName('bw-player')]
  players.forEach(createPlayer)
}

setupPlayers()
