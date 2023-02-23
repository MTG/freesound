const packSelectWrappers = document.getElementsByClassName('pack-select');

const togglePackNameDiv = (select, newPackNameDiv) => {
    if (select.value == '0'){
        newPackNameDiv.classList.remove('display-none');
    } else {
        newPackNameDiv.classList.add('display-none');
    }
}

packSelectWrappers.forEach(selectWrapper => {
    // Add event listener to toggle "new pack name" div if "create new pack" is selected
    const select = selectWrapper.getElementsByTagName('select')[0];
    const newPackNameDiv = selectWrapper.parentNode.getElementsByClassName('new-pack-name')[0];
    togglePackNameDiv(select, newPackNameDiv);
    select.addEventListener('change', (event) => {
        togglePackNameDiv(select, newPackNameDiv);
    });
});