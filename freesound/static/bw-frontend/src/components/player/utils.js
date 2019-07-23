/* eslint-disable import/prefer-default-export */
/**
 * @param {number} value
 */
const padSingleDigits = value => (value < 10 ? `0${value}` : value)

/**
 * @param {number} duration
 */
export const formatAudioDuration = duration => {
  const minutes = Math.floor(duration / 60)
  const seconds = Math.floor(duration % 60)
  return `${padSingleDigits(minutes)}:${padSingleDigits(seconds)}`
}
