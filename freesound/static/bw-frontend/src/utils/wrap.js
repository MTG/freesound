var wrapInDiv = (toWrap, wrapperClass) => {
  const wrapper = document.createElement('div');
  wrapper.classList = wrapperClass;
  toWrap.parentNode.insertBefore(wrapper, toWrap);
  return wrapper.appendChild(toWrap);
};

export { wrapInDiv };
