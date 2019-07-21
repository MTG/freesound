/* eslint-disable import/prefer-default-export */
import playerSettings from './settings'
import { formatAudioDuration } from './utils'
import { createIconElement } from '../../utils/icons'

const useActionIcon = (parentNode, action) => {
  const bwPlayBtn = parentNode.getElementsByClassName('bw-player__play-btn')[0]
  const playerStatusIcon = bwPlayBtn.getElementsByTagName('i')[0]
  const pauseIcon = createIconElement(`bw-icon-${action}`)
  bwPlayBtn.replaceChild(pauseIcon, playerStatusIcon)
}

/**
 * @param {number} progressPercentage
 * @param {HTMLDivElement} parentNode
 */
export const setProgressIndicator = (progressPercentage, parentNode) => {
  const progressIndicator = parentNode.getElementsByClassName(
    'bw-player__progress-indicator'
  )[0]
  progressIndicator.style.transform = `translateX(${-100 +
    progressPercentage}%)`
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {HTMLDivElement} parentNode
 */
const usePlayingAnimation = (audioElement, parentNode) => {
  const { duration, currentTime } = audioElement
  const progress = Math.ceil((currentTime / duration) * 100)
  setProgressIndicator(progress, parentNode)
  if (!audioElement.paused) {
    window.requestAnimationFrame(() =>
      usePlayingAnimation(audioElement, parentNode)
    )
  }
}

const usePlayingStatus = (audioElement, parentNode) => {
  parentNode.classList.add('bw-player--playing')
  useActionIcon(parentNode, 'pause')
  requestAnimationFrame(() => usePlayingAnimation(audioElement, parentNode))
}

/**
 * @param {HTMLDivElement} parentNode
 * @param {HTMLAudioElement} audioElement
 */
const removePlayingStatus = (parentNode, audioElement) => {
  parentNode.classList.remove('bw-player--playing')
  useActionIcon(parentNode, 'play')
  const didReachTheEnd = audioElement.duration === audioElement.currentTime
  if (didReachTheEnd) {
    setTimeout(() => setProgressIndicator(0, parentNode), 100)
  }
}

const onPlayerTimeUpdate = (audioElement, parentNode) => {
  const progressStatus = parentNode.getElementsByClassName(
    'bw-player__progress'
  )[0]
  const { duration, currentTime } = audioElement
  const progress = playerSettings.showRemainingTime
    ? duration - currentTime
    : currentTime
  progressStatus.innerHTML = `${
    playerSettings.showRemainingTime ? '-' : ''
  }${formatAudioDuration(progress)}`
}

/**
 * @param {HTMLDivElement} parentNode
 * @returns {HTMLAudioElement}
 */
export const createAudioElement = parentNode => {
  const { mp3, ogg } = parentNode.dataset
  const audioElement = document.createElement('audio')
  audioElement.setAttribute('controls', true)
  audioElement.setAttribute('controlslist', 'nodownload')
  const mp3Source = document.createElement('source')
  mp3Source.setAttribute('src', mp3)
  mp3Source.setAttribute('type', 'audio/mpeg')
  const oggSource = document.createElement('source')
  oggSource.setAttribute('src', ogg)
  oggSource.setAttribute('type', 'audio/ogg')
  audioElement.appendChild(mp3Source)
  audioElement.appendChild(oggSource)
  audioElement.addEventListener('play', () => {
    usePlayingStatus(audioElement, parentNode)
  })
  audioElement.addEventListener('pause', () => {
    removePlayingStatus(parentNode, audioElement)
  })
  audioElement.addEventListener('timeupdate', () => {
    onPlayerTimeUpdate(audioElement, parentNode)
  })
  return audioElement
}
