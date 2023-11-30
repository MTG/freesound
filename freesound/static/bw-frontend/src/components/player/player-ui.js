/* eslint-disable no-param-reassign */
import throttle from 'lodash.throttle'
import playerSettings from './settings'
import { formatAudioDuration, playAtTime, getAudioElementDurationOrDurationProperty, stopAllPlayers, simultaneousPlaybackDisallowed } from './utils'
import { createIconElement } from '../../utils/icons'
import { createAudioElement, setProgressIndicator, onPlayerTimeUpdate } from './audio-element'
import { rulerFrequencyMapping } from './utils'

const removeAllLastPlayedClasses = () => {
  document.getElementsByClassName('last-played').forEach(element => {
    element.classList.remove('last-played');
  });
}

const isTouchEnabledDevice = () => {
  return (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0))
}

if (isTouchEnabledDevice()){
  document.addEventListener('click', (evt) => {
    /* In touch devics, make sure we remove the last-played class when user touches
    somewhere outside a player */
    if (evt.target.closest('.bw-player') === null){
      removeAllLastPlayedClasses();
    }
  })
}

const replaceTimesinceIndicators = (parentNode) => {
  // Checks if timesince information has been added in the player metadata and if so, finds if there are
  // any elements with class timesince-target and replaces their content with the timesince information
  // NOTE: this modifies the sound display UI, not only strictly the "player" UI, but it's here because
  // because this seems the best place to handle this logic
  if (parentNode.dataset.timesince !== undefined){
    parentNode.parentNode.getElementsByClassName('timesince-target').forEach(timesinceTargetElement => {
      timesinceTargetElement.innerHTML = parentNode.dataset.timesince + ' ago';
    });
  }
}

const updateProgressBarIndicator = (parentNode, audioElement, progressPercentage) => {
  const progressBar = parentNode.getElementsByClassName('bw-player__progress-bar')[0]
  if (progressBar !== undefined) { // progress bar is only there in big players
    const progressBarIndicatorGhost = progressBar.getElementsByClassName('bw-player__progress-bar-indicator--ghost')[0]
    const progressBarTime = progressBar.getElementsByClassName('bw-player__progress-bar-indicator--time')[0]
    const progressBarIndicator = progressBar.getElementsByClassName('bw-player__progress-bar-indicator')[0]
    const width = progressBarIndicator.parentElement.clientWidth - progressBarIndicator.clientWidth
    progressBarIndicatorGhost.style.transform = `translateX(${width * progressPercentage}px)`
    progressBarIndicatorGhost.style.opacity = 0.5
    progressBarTime.style.transform = `translateX(calc(${width * progressPercentage}px - 50%))`
    progressBarTime.style.opacity = 1
    const duration = getAudioElementDurationOrDurationProperty(audioElement, parentNode);
    progressBarTime.innerHTML = formatAudioDuration(duration * progressPercentage, true)
  }
}

export const hideProgressBarIndicator = (parentNode) => {
  const progressBar = parentNode.getElementsByClassName('bw-player__progress-bar')[0]
  if (progressBar !== undefined) { // progress bar is only there in big players
    const progressBarIndicatorGhost = progressBar.getElementsByClassName('bw-player__progress-bar-indicator--ghost')[0]
    const progressBarTime = progressBar.getElementsByClassName('bw-player__progress-bar-indicator--time')[0]
    progressBarIndicatorGhost.style.opacity = 0
    progressBarTime.style.opacity = 0
  }
}

/**
 *
 * @param {HTMLDivElement} parentNode
 * @param {HTMLAudioElement} audioElement
 * @param {'small' | 'big'} playerSize
 */
const createProgressIndicator = (parentNode, audioElement, playerImgNode, playerSize) => {
  const progressIndicatorContainer = document.createElement('div')
  progressIndicatorContainer.className =
    'bw-player__progress-indicator-container'
  const progressIndicator = document.createElement('div')
  progressIndicator.className = 'bw-player__progress-indicator'
  if (playerSize === 'big'){
    progressIndicator.classList.add('bw-player--big')
  }
  progressIndicatorContainer.appendChild(progressIndicator)
  progressIndicatorContainer.addEventListener(
    'mousemove',
    throttle(evt => {
      if (parentNode.dataset.rulerActive) {
        const imgHeight = playerImgNode.clientHeight;
        const showingSpectrogram = playerImgNode.src.indexOf(parentNode.dataset.waveform) === -1;
        let readout = "";
        const posY = Math.min(evt.offsetY, imgHeight);
        const height2 = imgHeight/2;
        if (showingSpectrogram) {
          const sampleRate = parseFloat(parentNode.dataset.samplerate, 10);
          const srScaleCorrection = sampleRate/44100.0
          readout = (srScaleCorrection * rulerFrequencyMapping[Math.floor((posY/imgHeight) * 500.0)]).toFixed(2) + " Hz";
        } else {
          if (posY == height2)
              readout = "-inf";
          else
              readout = (20 * Math.log( Math.abs(posY/height2 - 1) ) / Math.LN10).toFixed(2);
          readout = readout + " dB";
        }
        const rulerIndicator = playerImgNode.parentNode.getElementsByClassName('bw-player__ruler-indicator')[0];
        rulerIndicator.innerText = readout;
      } else {
        // Update playhead
        const progressPercentage = evt.offsetX / progressIndicatorContainer.clientWidth
        setProgressIndicator(progressPercentage * 100, parentNode)

        // Update selected time indicator (only in big players)
        updateProgressBarIndicator(parentNode, audioElement, progressPercentage)
      }
    }),
    50
  )
  progressIndicatorContainer.addEventListener('mouseleave', () => {
    // Update playhead
    const duration = getAudioElementDurationOrDurationProperty(audioElement, parentNode);
    setProgressIndicator(
      ((100 * audioElement.currentTime) / duration) % 100,
      parentNode
    )
    
    // Update selected time indicator (only in big players)
    hideProgressBarIndicator(parentNode)
  })
  return progressIndicatorContainer
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {number} duration
 */
const createProgressBar = (audioElement, duration) => {
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
  progressBar.style.pointerEvents = "none";  // Do that so mouse events are propagated to the progress indicator layer
  return progressBar
}

/**
* @param {HTMLDivElement} parentNode
* @param {HTMLAudioElement} audioElement
 * @param {'small' | 'big'} playerSize
 * @param {bool} startWithSpectrum
 */
const createProgressStatus = (parentNode, audioElement, playerSize, startWithSpectrum) => {
  let { duration } = audioElement
  if ((duration === Infinity) || (isNaN(duration))){
    // Duration was not properly retrieved from audioElement. If given from data property, use that one.
    if (parentNode.dataset.duration !== undefined){
      duration = parseFloat(parentNode.dataset.duration)
    }
  }
  const progressStatusContainer = document.createElement('div')
  progressStatusContainer.className = 'bw-player__progress-container'
  const progressBar = createProgressBar(audioElement, duration)
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
  durationIndicator.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(duration, parentNode.dataset.showMilliseconds)}`
  progressIndicator.innerHTML = formatAudioDuration(0, parentNode.dataset.showMilliseconds)
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
  controlButton.type = 'button'
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
  playButton.setAttribute('title', 'Play/Pause')
  playButton.setAttribute('aria-label', 'Play/Pause')
  playButton.classList.add('bw-player__play-btn')
  playButton.addEventListener('pointerdown', evt => {evt.stopPropagation()})
  playButton.addEventListener('click', (evt) => {
    const isPlaying = !audioElement.paused
    if (isPlaying) {
      audioElement.pause()
    } else {
      if (simultaneousPlaybackDisallowed() || evt.altKey){
        stopAllPlayers();
      }
      audioElement.play()
    }
    evt.stopPropagation()
  })
  return playButton
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {HTMLDivElement} parentNode
 */
const createStopButton = (audioElement, parentNode) => {
  const stopButton = createControlButton('stop')
  stopButton.setAttribute('title', 'Stop')
  stopButton.setAttribute('aria-label', 'Stop')
  stopButton.addEventListener('pointerdown', evt => evt.stopPropagation())
  stopButton.addEventListener('click', (e) => {
    audioElement.pause()
    audioElement.currentTime = 0
    setProgressIndicator(0, parentNode)
    onPlayerTimeUpdate(audioElement, parentNode)
    e.stopPropagation()
  })
  return stopButton
}

/**
 * @param {HTMLAudioElement} audioElement
 */
const createLoopButton = audioElement => {
  const loopButton = createControlButton('loop')
  loopButton.setAttribute('title', 'Loop')
  loopButton.setAttribute('aria-label', 'Loop')
  loopButton.classList.add('text-20')
  loopButton.classList.add('loop-button')
  loopButton.addEventListener('pointerdown', evt => evt.stopPropagation())
  loopButton.addEventListener('click', (evt) => {
    const willLoop = !audioElement.loop
    if (willLoop) {
      loopButton.classList.add('text-red-important')
    } else {
      loopButton.classList.remove('text-red-important')
    }
    audioElement.loop = willLoop
    evt.stopPropagation()
  })
  return loopButton
}

const toggleSpectrogramWaveform = (playerImgNode, waveform, spectrum, playerSize) => {
  const controlsElement = playerImgNode.parentElement.querySelector('.bw-player__controls');
  const progressStatusContainerElement = playerImgNode.parentElement.querySelector('.bw-player__progress-container');
  const topControlsElement = playerImgNode.parentElement.querySelector('.bw-player__top_controls');
  const topControlsLeftElement = playerImgNode.parentElement.querySelector('.bw-player__top_controls_left');
  const bookmarkElement = playerImgNode.parentElement.querySelector('.bw-player__favorite');
  const similarSoundsElement = playerImgNode.parentElement.querySelector('.bw-player__similar');
  const remixSoundsElement = playerImgNode.parentElement.querySelector('.bw-player__remix');
  let spectrogramButton = undefined;
  try {
    spectrogramButton = controlsElement.querySelector('i.bw-icon-spectogram').parentElement;
  } catch (error){}
  const hasWaveform = playerImgNode.src.indexOf(waveform) > -1
  if (hasWaveform) {
    playerImgNode.src = spectrum
    if (spectrogramButton !== undefined){
      spectrogramButton.classList.add('text-red-important')
    }
    controlsElement.classList.add('bw-player__controls-inverted');
    topControlsElement.classList.add('bw-player__controls-inverted');
    if (topControlsLeftElement !== null){
      topControlsLeftElement.classList.add('bw-player__controls-inverted');
    }
    if (bookmarkElement !== null){
      bookmarkElement.classList.add('bw-player__controls-inverted');
    }
    if (similarSoundsElement !== null){
      similarSoundsElement.classList.add('bw-player__controls-inverted');
    }
    if (remixSoundsElement !== null){
      remixSoundsElement.classList.add('bw-player__controls-inverted');
    }
    if (progressStatusContainerElement !== null){
      progressStatusContainerElement.classList.add('bw-player__progress-container--inverted');
    }
  } else {
    playerImgNode.src = waveform
    if (spectrogramButton !== undefined){
      spectrogramButton.classList.remove('text-red-important')
    }
    controlsElement.classList.remove('bw-player__controls-inverted');
    topControlsElement.classList.remove('bw-player__controls-inverted');
    if (topControlsLeftElement !== null){
      topControlsLeftElement.classList.remove('bw-player__controls-inverted');
    }
    if (bookmarkElement !== null){
      bookmarkElement.classList.remove('bw-player__controls-inverted');
    }
    if (similarSoundsElement !== null){
      similarSoundsElement.classList.remove('bw-player__controls-inverted');
    }
    if (remixSoundsElement !== null){
      remixSoundsElement.classList.remove('bw-player__controls-inverted');
    }
    if (progressStatusContainerElement !== null){
      progressStatusContainerElement.classList.remove('bw-player__progress-container--inverted');
    }
  }
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
  spectogramButton.setAttribute('title', 'Spectrogram/Waveform')
  spectogramButton.setAttribute('aria-label', 'Spectrogram/Waveform')
  const { spectrum, waveform } = parentNode.dataset
  if (startWithSpectrum){
    spectogramButton.classList.add('text-red-important');
  }
  spectogramButton.addEventListener('pointerdown', evt => evt.stopPropagation())
  spectogramButton.addEventListener('click', evt => {
    toggleSpectrogramWaveform(playerImgNode, waveform, spectrum, playerSize)
    evt.stopPropagation()
  })
  return spectogramButton
}

const createRulerButton = (parentNode) => {
  const rulerButton = createControlButton('ruler')
  rulerButton.setAttribute('title', 'Ruler')
  rulerButton.setAttribute('aria-label', 'Ruler')
  rulerButton.classList.add('text-20')
  rulerButton.addEventListener('pointerdown', evt => evt.stopPropagation())
  rulerButton.addEventListener('click', evt => {
    if (parentNode.dataset.rulerActive !== undefined){
      delete parentNode.dataset.rulerActive;
    } else {
      parentNode.dataset.rulerActive = true;
    }
    const rulerIndicator = parentNode.getElementsByClassName('bw-player__ruler-indicator')[0];
    if (parentNode.dataset.rulerActive){
      rulerButton.classList.add('text-red-important');
      rulerIndicator.classList.add('opacity-090');
    } else {
      rulerButton.classList.remove('text-red-important');
      rulerIndicator.classList.remove('opacity-090');
    }
    evt.stopPropagation()
  })

  return rulerButton
}

const createRulerIndicator = (playerImage) => {
  const rulerIndicator = document.createElement('div')
  rulerIndicator.className = 'bw-player__ruler-indicator h-spacing-2'
  rulerIndicator.innerText = '-12.45 dB'
  rulerIndicator.style.pointerEvents = "none";  // Do that so mouse events are propagated to the progress indicator layer
  return rulerIndicator
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
    const {waveform, spectrum, title} = parentNode.dataset
    const playerImage = document.createElement('img')
    playerImage.setAttribute('loading', 'lazy');
    playerImage.className = 'bw-player__img'
    if (startWithSpectrum) {
      playerImage.src = spectrum
    } else {
      playerImage.src = waveform
    }
    playerImage.alt = title
    const progressIndicator = createProgressIndicator(parentNode, audioElement, playerImage, playerSize)
    imageContainer.appendChild(playerImage)
    imageContainer.appendChild(progressIndicator)
    const progressStatus = createProgressStatus(parentNode, audioElement, playerSize, startWithSpectrum)
    imageContainer.appendChild(progressStatus)

    imageContainer.addEventListener('pointerdown', evt => {  // We use "pointerdown" here so we can distinguish between mouse and touch events
      if (evt.altKey){
        toggleSpectrogramWaveform(playerImage, waveform, spectrum, playerSize);
      } else {
        const clickPosition = evt.offsetX
        const width = evt.target.clientWidth
        let positionRatio = clickPosition / width
        if (playerSize === "small"){
          if (evt.pointerType === "touch" && !parentNode.classList.contains('last-played') && audioElement.paused) {
            // In small player, if interaction is via touch and the audio is not yet playing and the player is not "focused", we ignore 
            // positionRatio and always start playing sound from the beggning. Then, a second touch (the audio is already playing) will 
            // play the sound from the position of the touch
            positionRatio = 0.0
          } else if (positionRatio < 0.05){
            // In small player and non-touch devices, we dome some quantization to start playing sound from the beggining when user clicks close enough to the start
            positionRatio = 0.0
          }
        }
        const duration = getAudioElementDurationOrDurationProperty(audioElement, parentNode);
        const time = duration * positionRatio
        if (audioElement.paused) {
          // If paused, use playAtTime util function because it supports setting currentTime event if data is not yet loaded
          playAtTime(audioElement, time)
        } else {
          // If already playing, using a touch event and the player is not "focused", then stop the player. Otherwise
          // set the new player position to the touch/click position
          if (evt.pointerType === "touch" && !parentNode.classList.contains('last-played')) {
            audioElement.pause()
            audioElement.currentTime = 0
            setProgressIndicator(0, parentNode)
            onPlayerTimeUpdate(audioElement, parentNode)
          } else {
            audioElement.currentTime = time
          }
        }
        if (isTouchEnabledDevice()){
          // In touch enabled devices hide the progress indicator here because otherwise it will remain visible as no
          // mouseleave event is ever fired
          hideProgressBarIndicator(parentNode)
        }
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
  playerControls.className = 'bw-player__controls'
  playerControls.addEventListener('click', evt => evt.stopPropagation())
  playerControls.addEventListener('pointerdown', evt => evt.stopPropagation())
  if (playerSize === 'big') {
    playerControls.classList.add('bw-player__controls--big')
  } else if (playerSize === 'minimal') {
    playerControls.classList.add('bw-player__controls--minimal')
  }

  if (isTouchEnabledDevice()){
    // For touch-devices (phones, tablets), we keep player controls always visible because hover tips are not that visible
    // Edit: play buttons are now always visible in both touch and non-touch devices, so this is not needed anymore
    // playerControls.classList.add('opacity-100')
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
         createRulerButton(parentNode)]
      : [createPlayButton(audioElement, playerSize),
         createLoopButton(audioElement)]
  controls.forEach(el => playerControls.appendChild(el))
  return playerControls
}

const createPlayerTopControls = (parentNode, playerImgNode, playerSize, showSimilarSoundsButton, showBookmarkButton, showRemixGroupButton) => {
  const topControls = document.createElement('div')
  topControls.className = 'bw-player__top_controls right'
  if (showRemixGroupButton){
    const remixGroupButton = createRemixGroupButton(parentNode, playerImgNode)
    topControls.appendChild(remixGroupButton)
  }
  if (showSimilarSoundsButton){
    const similarSoundsButton = createSimilarSoundsButton(parentNode, playerImgNode)
    topControls.appendChild(similarSoundsButton)
  }
  if (showBookmarkButton){
    const bookmarkButton = createSetFavoriteButton(parentNode, playerImgNode)
    topControls.appendChild(bookmarkButton)
  }
  if (playerSize == 'big'){
    const rulerIndicator = createRulerIndicator(playerImgNode);
    topControls.appendChild(rulerIndicator)
  }

  let startWithSpectrum = false;
  if (playerImgNode !== undefined){  // Some players don't have playerImgNode (minimal)
    startWithSpectrum = playerImgNode.src.indexOf(parentNode.dataset.waveform) === -1;
  }
  if (startWithSpectrum){
    topControls.classList.add('bw-player__controls-inverted');
  }

  return topControls;
}

/**
 *
 * @param {HTMLDivElement} parentNode
 * @param {HTMLImgElement} playerImgNode
 */
const createSetFavoriteButton = (parentNode, playerImgNode) => {
  const getIsFavorite = () => false // parentNode.dataset.favorite === 'true' // We always show the same button even if sound already bookmarked
  const favoriteButtonContainer = document.createElement('div')
  const favoriteButton = createControlButton('bookmark')
  const unfavoriteButton = createControlButton('bookmark-filled')
  favoriteButton.setAttribute('title', 'Bookmark this sound')
  favoriteButton.setAttribute('aria-label', 'Bookmark this sound')
  unfavoriteButton.setAttribute('title', 'Remove bookmark')
  unfavoriteButton.setAttribute('aria-label', 'Remove bookmark')
  favoriteButtonContainer.classList.add('bw-player__favorite')
  
  if (isTouchEnabledDevice()){
    // For touch-devices (phones, tablets), we keep player controls always visible because hover tips are not that visible
    // Edit: the bookmark button all alone makes players look ugly, so we don't make them always visible even in touch devices
    //favoriteButtonContainer.classList.add('opacity-050')
  }
  favoriteButtonContainer.setAttribute('data-toggle', 'bookmark-modal');
  favoriteButtonContainer.setAttribute('data-modal-url', parentNode.dataset.bookmarkModalUrl);
  favoriteButtonContainer.setAttribute('data-add-bookmark-url', parentNode.dataset.addBookmarkUrl);
  favoriteButtonContainer.appendChild(
    getIsFavorite() ? unfavoriteButton : favoriteButton
  )

  favoriteButtonContainer.addEventListener('pointerdown', evt => evt.stopPropagation())
  favoriteButtonContainer.addEventListener('click', (evt) => {
    const isCurrentlyFavorite = getIsFavorite()
    favoriteButtonContainer.innerHTML = ''
    favoriteButtonContainer.appendChild(
      isCurrentlyFavorite ? unfavoriteButton : favoriteButton
    )
    parentNode.dataset.favorite = `${!isCurrentlyFavorite}`
    evt.stopPropagation()
  })
  return favoriteButtonContainer
}

/**
 *
 * @param {HTMLDivElement} parentNode
 * @param {HTMLImgElement} playerImgNode
 */
const createSimilarSoundsButton = (parentNode, playerImgNode) => {
  const similarSoundsButtonContainer = document.createElement('div')
  const similarSoundsButton = createControlButton('similar')
  similarSoundsButton.setAttribute('title', 'Find similar sounds')
  similarSoundsButton.setAttribute('aria-label', 'Find similar sounds')
  similarSoundsButtonContainer.classList.add('bw-player__similar')
  similarSoundsButtonContainer.addEventListener('pointerdown', evt => evt.stopPropagation())
  similarSoundsButtonContainer.addEventListener('click', evt => evt.stopPropagation())
  
  if (isTouchEnabledDevice()){
    // For touch-devices (phones, tablets), we keep player controls always visible because hover tips are not that visible
    // Edit: the bookmark button all alone makes players look ugly, so we don't make them always visible even in touch devices
    //similarSoundsButtonContainer.classList.add('opacity-050')
  }
  similarSoundsButton.setAttribute('data-toggle', 'modal-default');
  similarSoundsButton.setAttribute('data-modal-content-url', parentNode.dataset.similarSoundsModalUrl);
  similarSoundsButtonContainer.appendChild(similarSoundsButton)
  return similarSoundsButtonContainer
}

/**
 *
 * @param {HTMLDivElement} parentNode
 * @param {HTMLImgElement} playerImgNode
 */
const createRemixGroupButton = (parentNode, playerImgNode) => {
  const remixGroupButtonContainer = document.createElement('div')
  const remixGroupButton = createControlButton('remix')
  remixGroupButton.setAttribute('title', 'See sound\'s remix group')
  remixGroupButton.setAttribute('aria-label', 'See sound\'s remix group')
  remixGroupButtonContainer.classList.add('bw-player__remix')
  remixGroupButtonContainer.addEventListener('pointerdown', evt => evt.stopPropagation())
  remixGroupButtonContainer.addEventListener('click', evt => evt.stopPropagation())
  
  if (isTouchEnabledDevice()){
    // For touch-devices (phones, tablets), we keep player controls always visible because hover tips are not that visible
    // Edit: the bookmark button all alone makes players look ugly, so we don't make them always visible even in touch devices
    //similarSoundsButtonContainer.classList.add('opacity-050')
  }
  remixGroupButton.setAttribute('data-toggle', 'remix-group-modal');
  remixGroupButton.setAttribute('data-modal-content-url', parentNode.dataset.remixGroupModalUrl);
  remixGroupButtonContainer.appendChild(remixGroupButton)
  return remixGroupButtonContainer
}


/**
 * @param {HTMLDivElement} parentNode
 */
const createPlayer = parentNode => {
  replaceTimesinceIndicators(parentNode);

  if (!isTouchEnabledDevice()){
    // If device is not touch enabled, then always enable hover interactions by adding appropriate class
    parentNode.classList.add('bw-player--hover-interactions')
  } else {
    // For mixed devices which support both touch and mouse, we'll manually add or remove the hover events class when appropriate
    parentNode.addEventListener('pointerenter', evt => {
      if (evt.pointerType !== 'mouse'){
        parentNode.classList.remove('bw-player--hover-interactions')
      } else {
        parentNode.classList.add('bw-player--hover-interactions')
      }
    })
    parentNode.addEventListener('pointerleave', evt => {
      parentNode.classList.remove('bw-player--hover-interactions')
    })
  }

  const playerSize = parentNode.dataset.size
  const showBookmarkButton = parentNode.dataset.bookmark === 'true'
  const showSimilarSoundsButton = parentNode.dataset.similarSounds === 'true'
  const showRemixGroupButton = parentNode.dataset.remixGroup === 'true'
  const audioElement = createAudioElement(parentNode)
  audioElement.addEventListener('play', () => {
    // When a player is played, add the last-played class to it and remove it from other players that might have it
    removeAllLastPlayedClasses();
    parentNode.classList.add('last-played');
  })
  const playerImage = createPlayerImage(
    parentNode,
    audioElement,
    playerSize
  )
  const playerImgNode = playerImage.getElementsByTagName('img')[0]
  parentNode.appendChild(playerImage)
  parentNode.appendChild(audioElement)
  const controls = createPlayerControls(parentNode, playerImgNode, audioElement, playerSize)
  playerImage.appendChild(controls)
  const topControls = createPlayerTopControls(parentNode, playerImgNode, playerSize, showSimilarSoundsButton, showBookmarkButton, showRemixGroupButton)
  playerImage.appendChild(topControls)

  const rateSoundHiddenWidget = parentNode.parentNode.getElementsByClassName('bw-player__rate__widget')[0]
  if (rateSoundHiddenWidget){
    const ratingWidget = document.createElement('div')
    ratingWidget.className = 'bw-player__top_controls_left'
    rateSoundHiddenWidget.classList.remove('display-none')
    ratingWidget.append(rateSoundHiddenWidget)
    ratingWidget.addEventListener('pointerdown', evt => evt.stopPropagation())
    ratingWidget.addEventListener('click', evt => evt.stopPropagation())
    let startWithSpectrum = false;
    if (playerImgNode !== undefined){  // Some players don't have playerImgNode (minimal)
      startWithSpectrum = playerImgNode.src.indexOf(parentNode.dataset.waveform) === -1;
    }
    if (startWithSpectrum){
      ratingWidget.classList.add('bw-player__controls-inverted');
    }
    playerImage.appendChild(ratingWidget)
  }

  setProgressIndicator(0, parentNode);
}


export {createPlayer, isTouchEnabledDevice};
