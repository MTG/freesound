import playerSettings from './settings'
import { formatAudioDuration } from './utils'
import { createIconElement } from '../../utils/icons'

const useActionIcon = (parentNode, action) => {
  const bwPlayBtn = parentNode.getElementsByClassName('bw-player__play-btn')[0]
  const playerStatusIcon = bwPlayBtn.getElementsByTagName('i')[0]
  const playerSize = parentNode.dataset.size
  const actionIcon = createIconElement(
    `bw-icon-${action}${playerSize === 'big' ? '-stroke' : ''}`
  )
  bwPlayBtn.replaceChild(actionIcon, playerStatusIcon)
}

/**
 * @param {number} progressPercentage
 * @param {HTMLDivElement} parentNode
 */
export const setProgressIndicator = (progressPercentage, parentNode) => {
  const progressIndicator = parentNode.getElementsByClassName(
    'bw-player__progress-indicator'
  )[0]
  const progressBarIndicator = parentNode.getElementsByClassName(
    'bw-player__progress-bar-indicator'
  )[0]

  if (progressIndicator) {
    const progressIndicatorRightBorderSize = progressIndicator.offsetWidth - progressIndicator.clientWidth
    const width = progressIndicator.parentElement.clientWidth - progressIndicatorRightBorderSize
    progressIndicator.style.transform = `translateX(${-width + ((width *
        progressPercentage) /
        100)}px)`
  }

  if (progressBarIndicator) {
    const width = progressBarIndicator.parentElement.clientWidth - progressBarIndicator.clientWidth
    progressBarIndicator.style.transform = `translateX(${(width *
      progressPercentage) /
      100}px)`
  }
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {HTMLDivElement} parentNode
 */
const usePlayingAnimation = (audioElement, parentNode) => {
  const { duration, currentTime } = audioElement
  const progress = (currentTime / duration) * 100
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
  const { duration, currentTime } = audioElement
  const didReachTheEnd = duration === currentTime
  // reset progress at the end of playback
  const timeElapsed = didReachTheEnd ? 0 : currentTime
  const progress = playerSettings.showRemainingTime
    ? duration - timeElapsed
    : timeElapsed

  const progressStatus = parentNode.getElementsByClassName('bw-player__progress')
  if (progressStatus.length > 0){
    // only show remaining time if progressStatus elements are found (e.g. in minimal player these elements are not included)
    const progressIndicator = [...progressStatus[0].childNodes][1]
    progressIndicator.innerHTML = `${
      playerSettings.showRemainingTime ? '-' : ''
    }${formatAudioDuration(progress)}`
  }
}

/**
 * @param {HTMLDivElement} parentNode
 * @returns {HTMLAudioElement}
 */
export const createAudioElement = parentNode => {
  const { mp3, ogg } = parentNode.dataset
  const audioElement = document.createElement('audio')
  audioElement.setAttribute('controls', true)
  audioElement.setAttribute('preload', 'metadata')
  audioElement.setAttribute('controlslist', 'nodownload')
  const mp3Source = document.createElement('source')
  mp3Source.setAttribute('src', mp3)
  mp3Source.setAttribute('type', 'audio/mpeg')
  const oggSource = document.createElement('source')
  oggSource.setAttribute('src', ogg)
  oggSource.setAttribute('type', 'audio/ogg')
  audioElement.appendChild(mp3Source)
  audioElement.appendChild(oggSource)

  let updatePlayerPositionTimer = undefined;

  audioElement.addEventListener('play', () => {
    usePlayingStatus(audioElement, parentNode);
    updatePlayerPositionTimer = setInterval(() => {
      onPlayerTimeUpdate(audioElement, parentNode)
  }, 100);

  })
  audioElement.addEventListener('pause', () => {
    removePlayingStatus(parentNode, audioElement)
    if (updatePlayerPositionTimer !== undefined){
      clearInterval(updatePlayerPositionTimer);
    }
  })

  return audioElement
}
