const padSingleDigits = number => (number < 10 ? `0${number}` : number);

// eslint-disable-next-line import/prefer-default-export
export const formatAudioDuration = duration => {
  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60);
  return `${padSingleDigits(minutes)}:${padSingleDigits(seconds)}`;
};
