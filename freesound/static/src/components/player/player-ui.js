import once from '../../utils/once';
import playerSettings from './settings';
import { formatAudioDuration } from './utils';
import { getIcon } from '../../utils/icons';

const players = [...document.getElementsByClassName('bw-player')];

const usePlayingStatus = (audioElement, parentNode) => {
  const progressIndicator = parentNode.getElementsByClassName('bw-player__progress-indicator')[0];
  const { duration } = audioElement;
  progressIndicator.style.animationDuration = `${duration}s`;
  progressIndicator.style.animationPlayState = 'running';
  parentNode.classList.add('bw-player--playing');
};

const removePlayingStatus = (audioElement, parentNode) => {
  parentNode.classList.remove('bw-player--playing');
  const progressIndicator = parentNode.getElementsByClassName('bw-player__progress-indicator')[0];
  progressIndicator.style.animationPlayState = 'paused';
};

const onPlayerTimeUpdate = (audioElement, parentNode) => {
  const progressStatus = parentNode.getElementsByClassName('bw-player__progress')[0];
  const { duration, currentTime } = audioElement;
  const progress = playerSettings.showRemainingTime ? duration - currentTime : currentTime;
  progressStatus.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(
    progress
  )}`;
};

const createProgressIndicator = () => {
  const progressIndicator = document.createElement('div');
  progressIndicator.className = 'bw-player__progress-indicator';
  return progressIndicator;
};

const createProgressStatus = audioElement => {
  const { duration } = audioElement;
  const progressStatus = document.createElement('div');
  progressStatus.className = 'bw-player__progress';
  progressStatus.innerHTML = `${playerSettings.showRemainingTime ? '-' : ''}${formatAudioDuration(
    duration
  )}`;
  return progressStatus;
};

const createPlayerControls = audioElement => {
  const playerControls = document.createElement('div');
  playerControls.className = 'bw-player__controls';
  const playButton = document.createElement('button');
  playButton.className = 'no-border-bottom-on-hover';
  playButton.appendChild(getIcon('play'));
  playButton.addEventListener('click', () => {
    const isPlaying = !audioElement.paused;
    const playerStatusIcon = playButton.getElementsByTagName('svg')[0];
    const playIcon = getIcon('play');
    const pauseIcon = getIcon('pause');
    if (isPlaying) {
      audioElement.pause();
      playButton.replaceChild(playIcon, playerStatusIcon);
    } else {
      audioElement.play();
      playButton.replaceChild(pauseIcon, playerStatusIcon);
    }
  });
  playerControls.appendChild(playButton);
  return playerControls;
};

const createWaveformImage = (parentNode, audioElement) => {
  const imageContainer = document.createElement('div');
  imageContainer.className = 'bw-player__img-container';
  const { waveform, title } = parentNode.dataset;
  const waveformImage = document.createElement('img');
  waveformImage.className = 'bw-player__img';
  waveformImage.src = waveform;
  waveformImage.alt = title;
  const progressIndicator = createProgressIndicator();
  const playerControls = createPlayerControls(audioElement, progressIndicator);
  imageContainer.appendChild(waveformImage);
  imageContainer.appendChild(progressIndicator);
  imageContainer.appendChild(playerControls);
  audioElement.addEventListener('loadedmetadata', () => {
    const progressStatus = createProgressStatus(audioElement);
    imageContainer.appendChild(progressStatus);
  });
  return imageContainer;
};

const createAudioElement = parentNode => {
  const { mp3, ogg } = parentNode.dataset;
  const audioElement = document.createElement('audio');
  audioElement.setAttribute('controls', true);
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
  });
  audioElement.addEventListener('pause', () => {
    removePlayingStatus(audioElement, parentNode);
  });
  audioElement.addEventListener('timeupdate', () => {
    onPlayerTimeUpdate(audioElement, parentNode);
  });
  return audioElement;
};

const createPlayer = parentNode => {
  const audioElement = createAudioElement(parentNode);
  const waveformImage = createWaveformImage(parentNode, audioElement);

  parentNode.appendChild(waveformImage);
  parentNode.appendChild(audioElement);
};

const setupPlayersOnce = once('player-setup', () => {
  players.forEach(createPlayer);
});

setupPlayersOnce();
