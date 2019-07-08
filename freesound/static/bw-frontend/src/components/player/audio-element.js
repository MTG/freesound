import playerSettings from './settings'
import { formatAudioDuration } from './utils'
import { createIconElement } from '../../utils/icons'

const useActionIcon = (parentNode, action) => {
  const bwPlayBtn = parentNode.getElementsByClassName('bw-player__play-btn')[0]
  const playerStatusIcon = bwPlayBtn.getElementsByTagName('i')[0]
  const pauseIcon = createIconElement(`bw-icon-${action}`)
  bwPlayBtn.replaceChild(pauseIcon, playerStatusIcon)
}

const usePlayingStatus = (audioElement, parentNode) => {
  const progressIndicator = parentNode.getElementsByClassName(
    'bw-player__progress-indicator'
  )[0]
  const { duration } = audioElement
  progressIndicator.style.animationDuration = `${duration}s`
  progressIndicator.style.animationPlayState = 'running'
  parentNode.classList.add('bw-player--playing')
  useActionIcon(parentNode, 'pause')
}

const removePlayingStatus = parentNode => {
  parentNode.classList.remove('bw-player--playing')
  const progressIndicator = parentNode.getElementsByClassName(
    'bw-player__progress-indicator'
  )[0]
  progressIndicator.style.animationPlayState = 'paused'
  useActionIcon(parentNode, 'play')
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
    removePlayingStatus(parentNode)
  })
  audioElement.addEventListener('timeupdate', () => {
    onPlayerTimeUpdate(audioElement, parentNode)
  })
  return audioElement
}
