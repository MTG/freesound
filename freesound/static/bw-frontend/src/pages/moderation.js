const selectAllButton = document.getElementById('select-all');
const selectOtherSoundsFromSameUser = document.getElementById('select-other');
const stopAllSounds = document.getElementById('stop-sounds');
const includeDeferredSoundsCheckbox = document.getElementById('include-deferred');
const autoplaySoundsCheckbox = document.getElementById('autoplay-sounds');
const moderateFormTitle = document.getElementById('moderate-form-title-label');
const moderateFormWrapper = document.getElementById('moderate-form-wrapper');
const ticketsTable = document.getElementById('assigned-tickets-table');
const ticketCheckboxes = ticketsTable.getElementsByClassName('bw-checkbox');

const allCheckboxesAreSelected = () => {
    for (let i = 0; i < ticketCheckboxes.length; i++) {
        if (!ticketCheckboxes[i].checked) {
            return false;
        }
    }
    return true;
}

const postTicketsSelected = () => {
    // Do things that need to be done after some tickets have been selected such as
    // showing sound information, etc.

    if (allCheckboxesAreSelected()) {
        selectAllButton.innerText = 'Unselect all';
    } else {
        selectAllButton.innerText = 'Select all';
    }
}

selectAllButton.addEventListener('click', () => {
    const shouldUnselect = allCheckboxesAreSelected()
    ticketCheckboxes.forEach(checkbox => {
        checkbox.checked = !shouldUnselect;
    });
    postTicketsSelected();
})

ticketCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', postTicketsSelected);
})