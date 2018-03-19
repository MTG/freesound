import once from '../../utils/once';

const players = [...document.getElementsByClassName('bw-player')];

const createWaveformImage = parentNode => {
  const { waveform, title } = parentNode.dataset;
  const waveformImage = document.createElement('img');
  waveformImage.className = 'bw-player-img';
  waveformImage.src = waveform;
  waveformImage.alt = title;
  return waveformImage;
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
