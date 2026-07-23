import playerSettings from './settings';
import {
  formatAudioDuration,
  getAudioElementDurationOrDurationProperty,
} from './utils';
import { createIconElement } from '../../utils/icons';

const useActionIcon = (parentNode, action) => {
  const bwPlayBtn = parentNode.getElementsByClassName('bw-player__play-btn')[0];
  const playerStatusIcon = bwPlayBtn.getElementsByTagName('i')[0];
  const playerSize = parentNode.dataset.size;
  const actionIcon = createIconElement(
    `bw-icon-${action}${playerSize === 'big' ? '-stroke' : ''}`
  );
  bwPlayBtn.replaceChild(actionIcon, playerStatusIcon);
};

/**
 * @param {number} progressPercentage
 * @param {HTMLDivElement} parentNode
 */
export const setProgressIndicator = (progressPercentage, parentNode) => {
  const progressIndicator = parentNode.getElementsByClassName(
    'bw-player__progress-indicator'
  )[0];
  const progressBarIndicator = parentNode.getElementsByClassName(
    'bw-player__progress-bar-indicator'
  )[0];

  if (progressPercentage == 0.0) {
    // When progress is at 0, move it to -1 so we make sure progress indicator does not appear
    progressPercentage = -1.0;
  }

  if (progressPercentage > 100) {
    // Make sure for any strange reason we don't go over
    progressPercentage = 100;
  }

  if (progressIndicator) {
    const progressIndicatorRightBorderSize =
      progressIndicator.offsetWidth - progressIndicator.clientWidth;
    const width =
      progressIndicator.parentElement.clientWidth -
      progressIndicatorRightBorderSize;
    progressIndicator.style.transform = `translateX(${-width + (width * progressPercentage) / 100}px)`;
  }

  if (progressBarIndicator) {
    if (progressPercentage < 0.0) {
      progressBarIndicator.style.opacity = 0.0;
    } else {
      progressBarIndicator.style.opacity = 1.0;
    }
    const width =
      progressBarIndicator.parentElement.clientWidth -
      progressBarIndicator.clientWidth;
    progressBarIndicator.style.transform = `translateX(${(width * progressPercentage) / 100}px)`;
  }
};

const getProgress = (audioElement, parentNode) => {
  const duration = getAudioElementDurationOrDurationProperty(
    audioElement.currentTime,
    parentNode
  );
  return (audioElement.currentTime / duration) * 100;
};

/**
 * @param {HTMLAudioElement} audioElement
 * @param {HTMLDivElement} parentNode
 */
const usePlayingAnimation = (audioElement, parentNode) => {
  let progress = getProgress(audioElement, parentNode);
  if (progress >= 100) {
    progress = 0;
  }
  setProgressIndicator(progress, parentNode);
  if (!audioElement.paused) {
    window.requestAnimationFrame(() =>
      usePlayingAnimation(audioElement, parentNode)
    );
  }
};

const usePlayingStatus = (audioElement, parentNode) => {
  parentNode.classList.add('bw-player--playing');
  useActionIcon(parentNode, 'pause');
  requestAnimationFrame(() => usePlayingAnimation(audioElement, parentNode));
};

/**
 * @param {HTMLDivElement} parentNode
 * @param {HTMLAudioElement} audioElement
 */
const removePlayingStatus = (parentNode, audioElement) => {
  parentNode.classList.remove('bw-player--playing');
  useActionIcon(parentNode, 'play');
  const duration = getAudioElementDurationOrDurationProperty(
    audioElement,
    parentNode
  );
  const didReachTheEnd = duration <= audioElement.currentTime;
  if (didReachTheEnd) {
    setTimeout(() => setProgressIndicator(0, parentNode), 100);
  }
};

export const onPlayerTimeUpdate = (audioElement, parentNode) => {
  const { currentTime } = audioElement;
  const duration = getAudioElementDurationOrDurationProperty(
    audioElement,
    parentNode
  );
  const didReachTheEnd = duration <= currentTime;
  // reset progress at the end of playback
  const timeElapsed = didReachTheEnd ? 0 : currentTime;
  const progress = playerSettings.showRemainingTime
    ? duration - timeElapsed
    : timeElapsed;
  const progressStatus = parentNode.getElementsByClassName(
    'bw-player__progress'
  );
  if (progressStatus.length > 0) {
    const progressIndicators = [...progressStatus[0].childNodes];
    if (parentNode.dataset.size === 'big') {
      // Big player, we update the indicator on the left with current progress
      const progressIndicatorLeft = progressIndicators[1];
      progressIndicatorLeft.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(progress, parentNode.dataset.showMilliseconds)}`;
    } else {
      // Small player, we update the indicator with current progress
      const progressIndicator = progressIndicators[0];
      if (!audioElement.paused) {
        progressIndicator.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(progress, parentNode.dataset.showMilliseconds)}`;
      } else {
        // In small player we show the full duration while sound is not playing
        // Note that we use the duration property from the sound player element which comes from database and not from the actual loaded preview
        // This is to avoid showing a different total duration once a preview is loaded
        progressIndicator.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(parentNode.dataset.duration, parentNode.dataset.showMilliseconds)}`;
      }
    }
  }
};

const clearPlayerUpdateInterval = parentNode => {
  if (parentNode.updatePlayerPositionTimer !== undefined) {
    clearInterval(parentNode.updatePlayerPositionTimer);
  }
};

/**
 * @param {HTMLDivElement} parentNode
 * @returns {HTMLAudioElement}
 */
export const createAudioElement = parentNode => {
  const { mp3, ogg } = parentNode.dataset;
  const audioElement = document.createElement('audio');
  audioElement.setAttribute('controls', true);
  audioElement.setAttribute('preload', 'none');
  audioElement.setAttribute('controlslist', 'nodownload');
  const mp3Source = document.createElement('source');
  mp3Source.setAttribute('src', mp3);
  mp3Source.setAttribute('type', 'audio/mpeg');
  const oggSource = document.createElement('source');
  oggSource.setAttribute('src', ogg);
  oggSource.setAttribute('type', 'audio/ogg');
  audioElement.appendChild(mp3Source);
  audioElement.appendChild(oggSource);

  audioElement.addEventListener('play', () => {
    usePlayingStatus(audioElement, parentNode);
    clearPlayerUpdateInterval(parentNode);
    parentNode.updatePlayerPositionTimer = setInterval(() => {
      onPlayerTimeUpdate(audioElement, parentNode);
    }, 30);
  });

  audioElement.addEventListener('ended', () => {
    audioElement.currentTime = 0.0;
    removePlayingStatus(parentNode, audioElement);
    clearPlayerUpdateInterval(parentNode);
    onPlayerTimeUpdate(audioElement, parentNode);
  });

  audioElement.addEventListener('pause', () => {
    removePlayingStatus(parentNode, audioElement);
    clearPlayerUpdateInterval(parentNode);
    onPlayerTimeUpdate(audioElement, parentNode);
  });

  return audioElement;
};
