const streamFormElement = document.getElementById('stream_form');
const selectElement = streamFormElement.getElementsByTagName('select')[0];
const dateInputElements = [
  document.getElementById('date_from'),
  document.getElementById('date_to'),
];

const enableOrDisableDateInputs = () => {
  if (selectElement.value == 'specific_dates') {
    dateInputElements.forEach(element => {
      element.disabled = false;
    });
  } else {
    dateInputElements.forEach(element => {
      element.disabled = true;
    });
  }
};

enableOrDisableDateInputs();

selectElement.addEventListener('change', e => {
  enableOrDisableDateInputs();
});
