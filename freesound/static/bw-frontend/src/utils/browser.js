import { UAParser } from 'ua-parser-js';

const { browser, cpu, device } = UAParser(navigator.userAgent);

const isIPad = () => {
  return device.model === 'iPad';
}

const isSafari = () => {
  return browser.name === 'Safari';
}

export const isTouchEnabledDevice = () => {
  return (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0))
}

export const isDesktopMacOSWithSafari = () => {
    return isSafari() && !isTouchEnabledDevice();
}

