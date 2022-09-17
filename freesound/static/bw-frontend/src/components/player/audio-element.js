// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import playerSettings from './settings'
import { formatAudioDuration, getAudioElementDurationOrDurationProperty } from './utils'
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
    progressIndicator.style.transform = `translateX(${-width + ((width * progressPercentage) / 100)}px)`
  }

  if (progressBarIndicator) {
    const width = progressBarIndicator.parentElement.clientWidth - progressBarIndicator.clientWidth
    progressBarIndicator.style.transform = `translateX(${(width * progressPercentage) / 100}px)`
  }


}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {HTMLDivElement} parentNode
 */
const usePlayingAnimation = (audioElement, parentNode) => {
  const { currentTime } = audioElement
  const duration = getAudioElementDurationOrDurationProperty(audioElement, parentNode);
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
  const duration = getAudioElementDurationOrDurationProperty(audioElement, parentNode)
  const didReachTheEnd = duration <= audioElement.currentTime
  if (didReachTheEnd) {
    setTimeout(() => setProgressIndicator(0, parentNode), 100)
  }
}

export const onPlayerTimeUpdate = (audioElement, parentNode) => {
  const { currentTime } = audioElement
  const duration = getAudioElementDurationOrDurationProperty(audioElement, parentNode)
  const didReachTheEnd = duration <= currentTime
  // reset progress at the end of playback
  const timeElapsed = didReachTheEnd ? 0 : currentTime
  const progress = playerSettings.showRemainingTime ? duration - timeElapsed: timeElapsed
  const progressStatus = parentNode.getElementsByClassName('bw-player__progress')
  if (progressStatus.length > 0){
    const progressIndicators = [...progressStatus[0].childNodes]
    if (parentNode.dataset.size === 'big') {
      // Big player, we update the indicator on the left with current progress
      const progressIndicatorLeft = progressIndicators[1]
      progressIndicatorLeft.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(progress, parentNode.dataset.showMilliseconds)}`
    } else {
      // Small player, we update the indicator with current progress
      const progressIndicator = progressIndicators[0]
      if (!audioElement.paused){
        progressIndicator.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(progress, parentNode.dataset.showMilliseconds)}`  
      } else {
        // In small player we show the full duration while sound is not playing
        // Note that we use the duration property from the sound player element which comes from database and not from the actual loaded preview
        // This is to avoid showing a different total duration once a preview is loaded
        progressIndicator.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(parentNode.dataset.duration, parentNode.dataset.showMilliseconds)}`  
      }
    }
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
  audioElement.setAttribute('preload', 'none')
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
    if (audioElement.readyState === 0){
      audioElement.addEventListener('loadeddata', () => {
        usePlayingStatus(audioElement, parentNode);
        updatePlayerPositionTimer = setInterval(() => {
          onPlayerTimeUpdate(audioElement, parentNode)
        }, 30)
      });
    } else {
      usePlayingStatus(audioElement, parentNode);
      updatePlayerPositionTimer = setInterval(() => {
        onPlayerTimeUpdate(audioElement, parentNode)
      }, 30)
    }
  })

  audioElement.addEventListener('ended', () => {
    onPlayerTimeUpdate(audioElement, parentNode);
  })

  audioElement.addEventListener('pause', () => {
    onPlayerTimeUpdate(audioElement, parentNode);
    removePlayingStatus(parentNode, audioElement)
    if (updatePlayerPositionTimer !== undefined){
      clearInterval(updatePlayerPositionTimer);
    }
  })

  return audioElement
}

// @license-end
