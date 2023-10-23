import {stopAllPlayers} from '../components/player/utils'

const selectAllButton = document.getElementById('select-all');
const selectNoneButton = document.getElementById('select-none');
const selectOtherFromSameUser = document.getElementById('select-other');
const stopAllSounds = document.getElementById('stop-sounds');
const includeDeferredTicketsCheckbox = document.getElementById('include-deferred');
const autoplaySoundsCheckbox = document.getElementById('autoplay-sounds');
const moderateFormTitle = document.getElementById('moderate-form-title-label');
const moderateFormWrapper = document.getElementById('moderate-form-wrapper');
const moderateForm = moderateFormWrapper.getElementsByTagName('form')[0];
const ticketsTable = document.getElementById('assigned-tickets-table');
const ticketCheckboxes = ticketsTable.getElementsByClassName('bw-checkbox');
const templateResponses = document.getElementById('template-responses').getElementsByTagName('a');
const messageTextArea = document.getElementsByName('message')[0];


const postTicketsSelected = () => {
    // Do things that need to be done after some tickets have been selected such as
    // showing sound information, etc.

    const selectedTicketsData = [];
    
    // Set css classes in table rows
    ticketCheckboxes.forEach(checkbox => {
        const trElement = checkbox.closest('tr');
        if (checkbox.checked) {
            trElement.classList.add('selected');
            selectedTicketsData.push({
                'soundId': trElement.dataset.soundId,
            });
        } else {
            trElement.classList.remove('selected');
        }
    });

    // Set moderation form tilte and show/hide moderation form
    if (selectedTicketsData.length === 0) {
        moderateFormWrapper.classList.add('display-none');
        
    } else {
        moderateFormWrapper.classList.remove('display-none');
        if (selectedTicketsData.length === 1) {
            moderateFormTitle.innerText = `Moderate sound ${selectedTicketsData[0]['soundId']}`;
        } else {
            moderateFormTitle.innerText = `Moderate ${selectedTicketsData.length} selected sounds`;
        }
    }

}

const shouldInludeDeferredTickets = () => {
    return includeDeferredTicketsCheckbox.checked;
}

const shouldAutoplaySounds = () => {
    return autoplaySoundsCheckbox.checked;
}

const correspondingTicketIsDeferred = (checkbox) => {
    return checkbox.closest('tr').dataset.ticketStatus === 'deferred';
}

const selectConsiderringDeferredStatus = (checkbox) => {
    const ticketIsDeferred = correspondingTicketIsDeferred(checkbox);
    if (!ticketIsDeferred) {
        checkbox.checked = true;
    } else {
        if (shouldInludeDeferredTickets()) {
            checkbox.checked = true;
        }
    }
}

selectAllButton.addEventListener('click', () => {
    ticketCheckboxes.forEach(checkbox => {
        selectConsiderringDeferredStatus(checkbox);
    });
    postTicketsSelected();
})

selectNoneButton.addEventListener('click', () => {
    ticketCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    postTicketsSelected();
})

selectOtherFromSameUser.addEventListener('click', () => {
    const selectedTicketUserIds = [];
    ticketCheckboxes.forEach(checkbox => {
        const userId = checkbox.closest('tr').dataset.senderId;
        if (checkbox.checked && selectedTicketUserIds.indexOf(userId) === -1) {
            selectedTicketUserIds.push(userId);
        }
    });
    ticketCheckboxes.forEach(checkbox => {
        const userId = checkbox.closest('tr').dataset.senderId;
        if (selectedTicketUserIds.indexOf(userId) !== -1) {
            selectConsiderringDeferredStatus(checkbox);
        };
    });
})

stopAllSounds.addEventListener('click', () => {
    stopAllPlayers();
})


ticketCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', postTicketsSelected);
})

moderateForm.addEventListener('submit', () => {
    var url = new URL(moderateForm.action);
    url.searchParams.set('include_d', shouldInludeDeferredTickets() ? 'on': 'off');
    url.searchParams.set('autoplay', shouldAutoplaySounds() ? 'on': 'off');
    moderateForm.action = url.href;
    return true;
})

templateResponses.forEach(templateResponse => {
    templateResponse.addEventListener('click', () => {
        messageTextArea.value = decodeURI(templateResponse.dataset.text);
    })
})

document.addEventListener("DOMContentLoaded", () => {
    if (ticketCheckboxes.length > 0){
        ticketCheckboxes[0].checked = true;
        postTicketsSelected();
    }
})