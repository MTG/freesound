import once from '../../utils/once';

const players = [...document.getElementsByClassName('bw-player')];

const usePlayingStatus = (audioElement, parentNode) => {
  const progressIndicator = parentNode.getElementsByClassName('bw-player__progress-indicator')[0];
  const { duration } = audioElement;
  progressIndicator.style.animationDuration = `${duration}s`;
  parentNode.classList.add('bw-player--playing');
};

const removePlayingStatus = (audioElement, parentNode) => {
  parentNode.classList.remove('bw-player--playing');
};

const onPlayerTimeUpdate = (audioElement, parentNode) => {
  // TODO
};

const createProgressIndicator = () => {
  const progressIndicator = document.createElement('div');
  progressIndicator.className = 'bw-player__progress-indicator';
  return progressIndicator;
};

const createWaveformImage = parentNode => {
  const imageContainer = document.createElement('div');
  imageContainer.className = 'bw-player__img-container';
  const { waveform, title } = parentNode.dataset;
  const waveformImage = document.createElement('img');
  waveformImage.className = 'bw-player__img';
  waveformImage.src = waveform;
  waveformImage.alt = title;
  const progressIndicator = createProgressIndicator();
  imageContainer.appendChild(waveformImage);
  imageContainer.appendChild(progressIndicator);
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
  const waveformImage = createWaveformImage(parentNode);
  const audioElement = createAudioElement(parentNode);

  parentNode.appendChild(waveformImage);
  parentNode.appendChild(audioElement);
};

const setupPlayersOnce = once('player-setup', () => {
  players.forEach(createPlayer);
});

setupPlayersOnce();
