const selectableSoundElements = [...document.getElementsByClassName('bw-selectable-sound')];
selectableSoundElements.forEach( element => {
    const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
    checkbox.addEventListener('change', evt => {
        if (checkbox.checked) {
            element.classList.add('selected');    
        } else {
            element.classList.remove('selected');
        }        
    });
});