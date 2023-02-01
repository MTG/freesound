const fileInputElement = document.getElementById('id_image-file');

const readURL = input => {
  if (input.files && input.files[0]) {
    var reader = new FileReader();
    reader.onload = function(e) {
      const imageProfileElement = document.getElementById('imageProfile');
      imageProfileElement.setAttribute('src', e.target.result);
      if (imageProfileElement.classList.contains('display-none')){
        imageProfileElement.classList.remove('display-none');  // If it was invisible, make new img avatar visible
        const noAvatarElement = imageProfileElement.nextElementSibling;
        noAvatarElement.classList.add('display-none'); // Make the no-avatar element invisible
      }
      const formElement = document.getElementById('avatarImageForm');
      formElement.submit();
    };

    reader.readAsDataURL(input.files[0]);
  }
};


if (fileInputElement) {
  fileInputElement.addEventListener('change', e => readURL(e.target));
}
