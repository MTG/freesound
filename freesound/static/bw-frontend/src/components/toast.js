let hideToastTimeout;

const wrapTextInUl = (text) => {
  // We wrap toast messages in ul/li so that they are formatted the same when returned from Django and when directly triggered in javascript
  if (text.indexOf('<ul>') === -1){
    return '<ul><li><span class="h-spacing-1">·</span>' + text + '</li></ul>';
  }
  return text;
}

export const showToast = (text, ulWrap) => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'block';
  if ((ulWrap === true) || (ulWrap === undefined)) {
    toastElement.children[0].innerHTML = wrapTextInUl(text);
  } else {
    toastElement.children[0].innerHTML = text;
  }
  hideToastTimeout = setTimeout(() => {
    toastElement.style.display = 'none';
  }, 10000);
};

export const showToastNoTimeout = (text, ulWrap) => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'block';
  if ((ulWrap === true) || (ulWrap === undefined)) {
    toastElement.children[0].innerHTML = wrapTextInUl(text);
  } else {
    toastElement.children[0].innerHTML = text;
  }
};

export const dismissToast = () => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'none';
};