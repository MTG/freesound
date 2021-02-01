const textareaInputElement = document.getElementById('about-edit-profile-textarea');
const fileInputElement = document.getElementById('file');

const readURL = input => {
  if (input.files && input.files[0]) {
    var reader = new FileReader();

    reader.onload = function(e) {
      document.getElementById('imageProfile').setAttribute('src', e.target.result);
    };

    reader.readAsDataURL(input.files[0]);
  }
};

const textareaCounter = value => {
  document.getElementById('counter-number').innerText = value.length;
};

fileInputElement.addEventListener('change', e => readURL(e.target));
textareaInputElement.addEventListener('keyup', e => textareaCounter(e.target.value));
