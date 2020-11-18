const taps = [...document.querySelectorAll('[data-toggle="tap"]')];

const cleanActiveClass = () => {
  taps.forEach(tap => tap.classList.remove('active'));
};

const handleTap = tap => {
  cleanActiveClass();
  console.log('handleTap', tap);
  tap.classList.add('active');
};

taps.forEach(tap => {
  tap.addEventListener('click', () => handleTap(tap));
});
