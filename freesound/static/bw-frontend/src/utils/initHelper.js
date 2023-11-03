import { makeSoundPlayers } from '../components/player/utils.js';
import { prepareAsyncSections } from '../components/asyncSection.js';
import { bindBookmarkSoundModals } from '../components/bookmarkSound.js';
import { makeCarousels } from '../components/carousel.js';
import { makeCheckboxes } from '../components/checkbox.js';
import { makeCollapsableBlocks } from '../components/collapsableBlock.js';
import { makeDropdowns } from '../components/dropdown.js';
import { addExplicitSoundWarnings } from '../components/explicit.js';
import { bindFlagUserButtons } from '../components/flagging.js';
import { bindFollowTagsButtons } from '../components/followUnfollowTags.js';
import { bindDisableOnSubmitForms } from '../components/formDisableOnSubmit.js';
import { bindDoNotSubmitOnEnterForms } from '../components/formDoNotSubmitOnEnter.js';
import { addSearchIconToInputs } from '../components/input.js';
import { bindConfirmationModalElements, bindDefaultModals, activateDefaultModalsIfParameters } from '../components/modal.js';
import { bindUserAnnotationsModal, activateUserAnnotationsModalIfParameters} from '../components/userAnnotationsModal.js';
import { makeRadios } from '../components/radio.js';
import { makeRatingWidgets } from '../components/rating.js';
import { bindRemixGroupModals, activateRemixGroupModalsIfParameters } from '../components/remixGroupModal.js';
import { makeSelect } from '../components/select.js';
import { makeTextareaCharacterCounter } from '../components/textareaCharactersCounter.js';
import { bindUnsecureImageCheckListeners } from '../components/unsecureImageCheck.js';


const initializeStuffInContainer = (container, bindModals, activateModals) => {

    // Make UI elements
    makeSoundPlayers(container);
    makeCarousels(container);
    makeSelect(container);
    makeDropdowns(container);
    makeCheckboxes(container);
    makeRadios(container);
    makeRatingWidgets(container);
    makeTextareaCharacterCounter(container);
    makeCollapsableBlocks(container);
    addSearchIconToInputs(container);
    addExplicitSoundWarnings(container);

    // Bind actions to UI elements
    bindUnsecureImageCheckListeners(container);
    bindDoNotSubmitOnEnterForms(container);
    bindDisableOnSubmitForms(container);
    bindFlagUserButtons(container);
    bindFollowTagsButtons(container);
    prepareAsyncSections(container);

    // Bind modals
    if (bindModals === true){
        bindDefaultModals(container);
        bindConfirmationModalElements(container);
        bindRemixGroupModals(container);
        bindBookmarkSoundModals(container);
        bindUserAnnotationsModal(container); 
    }
    
    // Activate modals if needed (this should only be used the first time initializeStuffInContainer is called)
    if (activateModals === true){
        activateDefaultModalsIfParameters();
        activateUserAnnotationsModalIfParameters();
        activateRemixGroupModalsIfParameters();
    }
}

export { initializeStuffInContainer };