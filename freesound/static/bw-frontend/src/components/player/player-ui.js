import playerSettings from './settings'
import { formatAudioDuration } from './utils'
import { createIconElement } from '../../utils/icons'
import { createAudioElement } from './audio-element'

const createProgressIndicator = () => {
  const progressIndicator = document.createElement('div')
  progressIndicator.className = 'bw-player__progress-indicator'
  return progressIndicator
}

const createProgressStatus = audioElement => {
  const { duration } = audioElement
  const progressStatus = document.createElement('div')
  progressStatus.className = 'bw-player__progress'
  progressStatus.innerHTML = `${
    playerSettings.showRemainingTime ? '-' : ''
  }${formatAudioDuration(duration)}`
  return progressStatus
}

const createPlayerControls = audioElement => {
  const playerControls = document.createElement('div')
  playerControls.className = 'bw-player__controls'
  const playButton = document.createElement('button')
  playButton.className = 'bw-player__play-btn no-border-bottom-on-hover'
  playButton.appendChild(createIconElement('bw-icon-play'))
  playButton.addEventListener('click', () => {
    const isPlaying = !audioElement.paused
    if (isPlaying) {
      audioElement.pause()
    } else {
      audioElement.play()
    }
  })
  playerControls.appendChild(playButton)
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
  const playerControls = createPlayerControls(audioElement)
  imageContainer.appendChild(waveformImage)
  imageContainer.appendChild(progressIndicator)
  imageContainer.appendChild(playerControls)
  audioElement.addEventListener('loadedmetadata', () => {
    const progressStatus = createProgressStatus(audioElement)
    imageContainer.appendChild(progressStatus)
  })
  return imageContainer
}

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
