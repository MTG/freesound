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
const ticketIdsInput = document.getElementsByName('ticket')[0];
const soundInfoElementsPool = document.getElementById('sound-info-elements');
const selectedSoundsInfoPanel = document.getElementById('selected-sounds-info');


const postTicketsSelected = () => {
    // Do things that need to be done after some tickets have been selected such as
    // showing sound information, etc.

    const selectedTicketsData = [];
    
    // Collect selection informaiton and set css classes in table rows
    ticketCheckboxes.forEach(checkbox => {
        const trElement = checkbox.closest('tr');
        if (checkbox.checked) {
            trElement.classList.add('selected');
            selectedTicketsData.push({
                'soundId': trElement.dataset.soundId,
                'ticketId': trElement.dataset.ticketId,
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

    // Set "ticket" field in moderation form with the ticket ids of the selected tickets
    const ticketIdsSerialized = selectedTicketsData.map(ticketData => ticketData['ticketId']).join('|');
    ticketIdsInput.value = ticketIdsSerialized;

    // Show information about the selected sounds
    // First move all selected sound info elements to the main pool
    while (selectedSoundsInfoPanel.childNodes.length > 0) {
        soundInfoElementsPool.appendChild(selectedSoundsInfoPanel.childNodes[0]);
    }

    // Then move the selected ones to the selected panel
    selectedTicketsData.forEach(ticketData => {
        const soundInfoElement = document.querySelector(`.sound-info-element[data-sound-id="${ticketData['soundId']}"]`);
        selectedSoundsInfoPanel.appendChild(soundInfoElement);
    });

    // Stop playing sounds if no tickets are selected
    if (selectedTicketsData.length === 0) {
        stopAllPlayers();
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
    // The click event below if used to detect if the user is holding the alt key when clicking the checkbox and so we can use that information
    // in the "change" event below (which otherwise does not hold information about the alt key)
    checkbox.addEventListener('click', (evt) => {
        checkbox.dataset.altKey = evt.altKey ? "true" : "false";
        setTimeout(() => {
            checkbox.dataset.altKey = false;
        }, 100);
    })

    // NOTE: the 'change' event is triggered when the checkbox is clicked by the user, but not when programatically setting .checked to true/false
    checkbox.addEventListener('change', () => {
        if (checkbox.dataset.altKey === "true") {
            // Unselect all other checkboxes
            ticketCheckboxes.forEach(otherCheckbox => {
                if (otherCheckbox !== checkbox) {
                    otherCheckbox.checked = false;
                }
            });
            // Make sure the clicked checkbox is selected (even if the change event would unselect it initially)
            checkbox.checked = true;
        }
        postTicketsSelected();

        // Manage sound playback
        const soundInfoElement = document.querySelector(`.sound-info-element[data-sound-id="${checkbox.closest('tr').dataset.soundId}"]`);
        const audioElement = soundInfoElement.getElementsByTagName('audio')[0];
        if (checkbox.checked) {
            // Trigger autoplay of the selected sound if autoplay is on 
            if (shouldAutoplaySounds()) {
                stopAllPlayers();
                audioElement.play();
                // NOTE: this can fail if autoplay is not allowed by the browser
            }
        } else {
            // Stop playing sound in case it was being played
            audioElement.pause();
            audioElement.currentTime = 0;
        }
    });
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