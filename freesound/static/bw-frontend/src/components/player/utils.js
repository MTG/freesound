/* eslint-disable import/prefer-default-export */
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
 */
export const formatAudioDuration = duration => {
  if (duration === Infinity){
    return `?:?:?`
  }
  const minutes = Math.floor(duration / 60)
  const seconds = Math.floor(duration % 60)
  const milliseconds = duration - Math.floor(duration)
  return `${padSingleDigits(minutes)}:${padSingleDigits(
    seconds
  )}:${formatMilliseconds(milliseconds)}`
}
