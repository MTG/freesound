/* eslint-disable import/prefer-default-export */

export const isTouchEnabledDevice = () => {
  return (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0))
}

export const simultaneousPlaybackDisallowed = () => {
  return document.cookie.indexOf('disallowSimultaneousAudioPlayback=yes') > -1;
}


/**
 * @param {number} value
 */
const padSingleDigits = value => (value < 10 ? `0${value}` : value)

/**
 * @param {number} value
 */
const formatMilliseconds = value => {
  const roundedValue = Math.floor(value * 1000)
  if (roundedValue < 10) {
    return `00${roundedValue}`
  }
  if (roundedValue < 100) {
    return `0${roundedValue}`
  }
  return roundedValue
}

/**
 * @param {number} duration
 * @param {string} showMilliseconds
 */
export const formatAudioDuration = (duration, showMilliseconds) => {
  if ((duration === Infinity) || (isNaN(duration))){
    return `?:?`
  }
  const minutes = Math.floor(duration / 60)
  const seconds = Math.floor(duration % 60)
  const milliseconds = duration - Math.floor(duration)
  if (showMilliseconds === "true" || showMilliseconds === true){
    return `${minutes}:${padSingleDigits(seconds)}.${formatMilliseconds(milliseconds)}`
  } else {
    return `${minutes}:${padSingleDigits(seconds)}`
  }
}


export const stopAllPlayers = () => {
  const players = [...document.getElementsByClassName('bw-player')]
  players.forEach(player => {
    player.getElementsByTagName('audio').forEach(audioElement=>{audioElement.pause()});
  });
}

/**
 * @param {HTMLAudioElement} audioElement
 * @param {number} timeInSeconds
 *
 * Starts to play the audio of an audioElement at the desired time in seconds. If the audioElement has not been
 * loaded, a load() is triggered and we wait until readyState is > 0 to start playing.
 */
export const playAtTime = (audioElement, timeInSeconds) => {
  if (audioElement.readyState > 0){
    // If player is ready to start playing, do it!
    audioElement.currentTime = timeInSeconds;
    if (simultaneousPlaybackDisallowed()){
      stopAllPlayers();
    }
    audioElement.play();
  } else {
    // If player needs to load data, trigger data loading and then play at the required time
    audioElement.load();
    audioElement.addEventListener('loadeddata', () => {
      audioElement.currentTime = timeInSeconds;
      if (simultaneousPlaybackDisallowed()){
        stopAllPlayers();
      }
      audioElement.play();
    });
  }
}


export const getAudioElementDurationOrDurationProperty = (audioElement, parentNode) => {
  let audioDuration;
    if (audioElement.readyState > 0){
      audioDuration = audioElement.duration
    } else {
      audioDuration = parseFloat(parentNode.dataset.duration)
    }
    return audioDuration;
}


export const rulerFrequencyMapping = [];
var y_min = Math.log(100.0) / Math.LN10;  // See utils.audioprocessing.processing.SpectrogramImage as this must match
var y_max = Math.log(22050.0) / Math.LN10;
for (var y = 500;y >= 0; y--)
  rulerFrequencyMapping.push(Math.pow(10.0, y_min + y / 500.0 * (y_max - y_min)));
