const fileInputElement = document.getElementById('id_image-file');

const readURL = input => {
  if (input.files && input.files[0]) {
    var reader = new FileReader();

    reader.onload = function(e) {
      document.getElementById('imageProfile').setAttribute('src', e.target.result);
      const formElement = document.getElementById('avatarImageForm');
      formElement.submit();
    };

    reader.readAsDataURL(input.files[0]);
  }
};


if (fileInputElement) {
  fileInputElement.addEventListener('change', e => readURL(e.target));
}


const updateTextareaCounter = (textareaInputElementId, value) => {
  document.getElementById(textareaInputElementId + '-counter-number').innerText = value.length;
};


[...document.getElementsByTagName('textarea')].forEach(textareaInputElement => {
  // For all textarea elements with "maxlength" arttribute, setup character counters
  if (textareaInputElement.hasAttribute('maxlength')) {
    textareaInputElement.parentNode.classList.add('bw-edit-profile__textarea_block');
    const counterElement = document.createElement('div');
    counterElement.classList.add('edit-profile-textarea-counter');
    counterElement.style.top = (textareaInputElement.offsetHeight + 7) + 'px';
    const leftSpan = document.createElement('span');
    leftSpan.innerHTML = textareaInputElement.value.length;
    leftSpan.id = textareaInputElement.id + '-counter-number';
    const rightSpan = document.createElement('span');
    rightSpan.innerHTML = '/' + textareaInputElement.getAttribute('maxlength');
    counterElement.appendChild(leftSpan);
    counterElement.appendChild(rightSpan);
    textareaInputElement.parentNode.appendChild(counterElement);
    textareaInputElement.addEventListener('keyup', e => updateTextareaCounter(textareaInputElement.id, e.target.value));
  }
});