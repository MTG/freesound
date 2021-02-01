const fileInputElement = document.getElementById('file');

const readURL = input => {
  console.log('readURL', input);
  if (input.files && input.files[0]) {
    var reader = new FileReader();

    reader.onload = function(e) {
      document.getElementById('imageProfile').setAttribute('src', e.target.result);
    };

    reader.readAsDataURL(input.files[0]);
  }
};

fileInputElement.addEventListener('change', e => readURL(e.target));
