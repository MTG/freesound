import { UAParser } from 'ua-parser-js';

const { browser, cpu, device } = UAParser(navigator.userAgent);

const isPhone = () => {
  return device.type === 'mobile';
};

const isSafari = () => {
  return browser.name === 'Safari';
};

export const isTouchEnabledDevice = () => {
  return (
    'ontouchstart' in window ||
    navigator.maxTouchPoints > 0 ||
    navigator.msMaxTouchPoints > 0
  );
};

export const isDesktopMacOSWithSafari = () => {
  return isSafari() && !isTouchEnabledDevice();
};

function update_viewport_width_if_needed() {
  const minWidth = isPhone() ? 1000 : 600;
  if (window.innerWidth < minWidth) {
    document
      .querySelector('meta[name="viewport"]')
      .setAttribute('content', 'width=0, initial-scale=0.8');
  } else {
    document
      .querySelector('meta[name="viewport"]')
      .setAttribute('content', 'width=0');
  }
}

update_viewport_width_if_needed();

window.addEventListener('resize', function (event) {
  update_viewport_width_if_needed();
});
