const addHorizontalSwipeListener = (element, callback) => {
  element.touchstartX = 0;
  element.touchstarttime = 0;

  function validSwipe(diffX, diffTime) {
    if (diffTime > 500) {
      return false;
    }
    if (Math.abs(diffX) < 100) {
      return false;
    }
    return true;
  }

  element.addEventListener('touchstart', e => {
    element.touchstartX = e.changedTouches[0].screenX;
    element.touchstarttime = e.timeStamp;
  });
  element.addEventListener('touchend', e => {
    const diffX = e.changedTouches[0].screenX - element.touchstartX;
    const diffTime = e.timeStamp - element.touchstarttime;
    if (validSwipe(diffX, diffTime)) {
      // Call callback with true if swipping right and false if swipping left
      callback(diffX > 0);
    }
  });
};

export { addHorizontalSwipeListener };
