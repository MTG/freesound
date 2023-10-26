import { stopAllPlayers } from '../components/player/utils'
import { getCookie, setCookie } from "../utils/cookies";

const selectAllButton = document.getElementById('select-all');
const selectNoneButton = document.getElementById('select-none');
const selectOtherFromSameUser = document.getElementById('select-other');
const stopAllSounds = document.getElementById('stop-sounds');
const includeDeferredTicketsCheckbox = document.getElementById('include-deferred');
const autoplaySoundsCheckbox = document.getElementById('autoplay-sounds');
const autoscrollSoundsCheckbox = document.getElementById('autoscroll-sounds');
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

    // If no sound is selected after this method is run, scroll window to top
    if (selectedTicketsData.length === 0) {
        document.documentElement.scrollTop = document.body.scrollTop = 0;
    }
}

const scrollWindowToSoundInfoElement = (soundId) => {
    if (selectedSoundsInfoPanel.offsetHeight - parseFloat(selectedSoundsInfoPanel.style.paddingBottom) + moderateForm.offsetHeight > window.innerHeight) {
        const soundInfoElement = selectedSoundsInfoPanel.querySelector(`.sound-info-element[data-sound-id="${soundId}"]`);
        if (soundInfoElement !== undefined){
            const amountToScroll = soundInfoElement.offsetTop + moderateForm.offsetHeight - 180;
            document.documentElement.scrollTop = document.body.scrollTop = amountToScroll;
        }
    } else {
        document.documentElement.scrollTop = document.body.scrollTop = 0;
    }
}

const shouldInludeDeferredTickets = () => {
    return includeDeferredTicketsCheckbox.checked;
}

const shouldAutoplaySounds = () => {
    return autoplaySoundsCheckbox.checked;
}

const shouldAutoscroll = () => {
    return autoscrollSoundsCheckbox.checked;
}

// set cookie when changing checkbox and set initial cookie value
if (getCookie('mod_include_d') === 'on') {
    includeDeferredTicketsCheckbox.checked = true;
}
if (getCookie('mod_autoplay') === 'on') {
    autoplaySoundsCheckbox.checked = true;
}
if (getCookie('mod_autoscroll') === 'on') {
    autoscrollSoundsCheckbox.checked = true;
}

includeDeferredTicketsCheckbox.addEventListener('change', (evt) => {
    setCookie('mod_include_d', evt.target.checked ? 'on' : 'off');
})

autoplaySoundsCheckbox.addEventListener('change', (evt) => {
    setCookie('mod_autoplay', evt.target.checked ? 'on' : 'off');
})

autoscrollSoundsCheckbox.addEventListener('change', (evt) => {
    setCookie('mod_autoscroll', evt.target.checked ? 'on' : 'off');
})

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
    postTicketsSelected();
})

stopAllSounds.addEventListener('click', () => {
    stopAllPlayers();
})

ticketCheckboxes.forEach(checkbox => {
    // The click event below if used to detect if the user is holding the alt key when clicking the checkbox and so we can use that information
    // in the "change" event below (which otherwise does not hold information about the alt key)
    checkbox.addEventListener('click', (evt) => {
        checkbox.dataset.altKey = evt.altKey ? "true" : "false";
        checkbox.dataset.shiftKey = evt.shiftKey ? "true" : "false";
        setTimeout(() => {
            checkbox.dataset.altKey = false;
            checkbox.dataset.shiftKey = false;
        }, 100);
    })

    // NOTE: the 'change' event is triggered when the checkbox is clicked by the user, but not when programatically setting .checked to true/false
    checkbox.addEventListener('change', () => {
        if (checkbox.dataset.altKey !== "true" && checkbox.dataset.shiftKey !== "true") {
            // If the current is being selected, then unselect all other checkboxes
            if (checkbox.checked) {
                ticketCheckboxes.forEach(otherCheckbox => {
                    if (otherCheckbox !== checkbox) {
                        otherCheckbox.checked = false;
                    }
                });
            }
        }
        let didMultipleSelection = false;
        if (checkbox.dataset.shiftKey === "true") {
            didMultipleSelection = true;
            // If holding shift, then do mulitple selection since the last selected checkbox
            let lastSelectedCheckbox = undefined;
            let shouldSkip = false;
            ticketCheckboxes.forEach(otherCheckbox => {
                if (!shouldSkip) {
                    if (otherCheckbox !== checkbox) {
                        if (otherCheckbox.checked) {
                            lastSelectedCheckbox = otherCheckbox;
                        }
                    } else {
                        // Once we iterated until the clicked checkbox, we stop
                        shouldSkip = true;
                    }
                }
            });
            if (lastSelectedCheckbox !== undefined) {
                // Now we mark all checkboxes between last selected checkbox and current checkbox as selected
                let selecting = false;
                ticketCheckboxes.forEach(otherCheckbox => {
                    if (otherCheckbox === lastSelectedCheckbox) {
                        selecting = true;
                    }
                    if (selecting) {
                        otherCheckbox.checked = true;
                    }
                    if (otherCheckbox === checkbox) {
                        selecting = false;
                    }
                }); 
            }
        }
        postTicketsSelected();

        // Manage sound playback
        const soundInfoElement = document.querySelector(`.sound-info-element[data-sound-id="${checkbox.closest('tr').dataset.soundId}"]`);
        const audioElement = soundInfoElement.getElementsByTagName('audio')[0];
        if (checkbox.checked) {
            // Trigger autoplay of the selected sound if autoplay is on 
            if (shouldAutoplaySounds() && !didMultipleSelection) {
                stopAllPlayers();
                audioElement.play();
                // NOTE: this can fail if autoplay is not allowed by the browser
            }
        } else {
            // Stop playing sound in case it was being played
            audioElement.pause();
            audioElement.currentTime = 0;
        }

        // Scroll to sound if not doing multiple selection and sound was checked
        if (shouldAutoscroll()) {
            if (!didMultipleSelection) {
                if (checkbox.checked) {
                    scrollWindowToSoundInfoElement(checkbox.closest('tr').dataset.soundId);
                } else {
                    // If unchecked, scroll a bit to top (the ammount of a sound info element)
                    const currentScrollPosition = document.documentElement.scrollTop;
                    document.documentElement.scrollTop = document.body.scrollTop = currentScrollPosition - soundInfoElement.offsetHeight;
                }
            }
        }
    });
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

// Highlight whitelist option in a different colour to avoid mistakes
const whitelistOptionLabelElement = document.querySelector("[for='id_action_4']");
whitelistOptionLabelElement.style = 'color:#0064af!important;'