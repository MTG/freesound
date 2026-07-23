let hideToastTimeout;
let hideToastAnimationTimeout;
const TOAST_ANIMATION_DURATION_MS = 260;

const showToastElement = toastElement => {
  clearTimeout(hideToastAnimationTimeout);
  toastElement.classList.remove('toast--hiding');
  toastElement.style.display = 'block';

  // Force reflow so the show animation restarts when toast is shown again.
  void toastElement.offsetWidth;
  toastElement.classList.add('toast--visible');
};

const hideToastElement = toastElement => {
  clearTimeout(hideToastAnimationTimeout);
  toastElement.classList.remove('toast--visible');
  toastElement.classList.add('toast--hiding');

  hideToastAnimationTimeout = setTimeout(() => {
    toastElement.classList.remove('toast--hiding');
    toastElement.style.display = 'none';
  }, TOAST_ANIMATION_DURATION_MS);
};

const wrapTextInUl = text => {
  // We wrap toast messages in ul/li so that they are formatted the same when returned from Django and when directly triggered in javascript
  if (text.indexOf('<ul>') === -1) {
    return '<ul><li><span class="h-spacing-1">·</span>' + text + '</li></ul>';
  }
  return text;
};

export const showToast = (text, ulWrap) => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  showToastElement(toastElement);
  if (ulWrap === true || ulWrap === undefined) {
    toastElement.children[0].innerHTML = wrapTextInUl(text);
  } else {
    toastElement.children[0].innerHTML = text;
  }
  hideToastTimeout = setTimeout(() => {
    hideToastElement(toastElement);
  }, 10000);
};

export const showToastNoTimeout = (text, ulWrap) => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  showToastElement(toastElement);
  if (ulWrap === true || ulWrap === undefined) {
    toastElement.children[0].innerHTML = wrapTextInUl(text);
  } else {
    toastElement.children[0].innerHTML = text;
  }
};

export const dismissToast = () => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  hideToastElement(toastElement);
};
