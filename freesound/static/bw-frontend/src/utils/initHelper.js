import { makeSoundPlayers } from '../components/player/utils.js';
import { prepareAsyncSections } from '../components/asyncSection.js';
import { bindBookmarkSoundModals } from '../components/bookmarkSound.js';
import { makeCarousels } from '../components/carousel.js';
import { makeCheckboxes } from '../components/checkbox.js';
import { makeCollapsableBlocks } from '../components/collapsableBlock.js';
import { bindCommentsModals, activateCommentsModalsIfParameters } from '../components/commentsModal.js';
import { bindDownloadersModals, activateDownloadersModalsIfParameters } from '../components/downloadersModals.js';
import { makeDropdowns } from '../components/dropdown.js';
import { addExplicitSoundWarnings } from '../components/explicit.js';
import { bindFlagUserButtons } from '../components/flagging.js';
import { bindFollowTagsButtons } from '../components/followUnfollowTags.js';
import { bindDisableOnSubmitForms } from '../components/formDisableOnSubmit.js';
import { bindDoNotSubmitOnEnterForms } from '../components/formDoNotSubmitOnEnter.js';
import { addSearchIconToInputs } from '../components/input.js';
import { bindConfirmationModalElements } from '../components/modal.js';
import { bindModerationModals, activateModerationModalsIfParameters } from '../components/moderationModals.js';
import { makeRadios } from '../components/radio.js';
import { makeRatingWidgets } from '../components/rating.js';
import { bindRemixGroupModals, activateRemixGroupModalsIfParameters } from '../components/remixGroupModal.js';
import { makeSelect } from '../components/select.js';
import { bindSimilarSoundModals, activateSimilarSoundsModalsIfParameters } from '../components/similarSoundsModal.js';
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
        bindConfirmationModalElements(container);
        bindBookmarkSoundModals(container);
        bindCommentsModals(container);
        bindDownloadersModals(container);
        bindModerationModals(container);
        bindRemixGroupModals(container);
        bindSimilarSoundModals(container);
    }
    
    // Activate modals if needed (this should only be used the first time initializeStuffInContainer is called)
    if (activateModals === true){
        activateDownloadersModalsIfParameters();
        activateCommentsModalsIfParameters();
        activateModerationModalsIfParameters();
        activateRemixGroupModalsIfParameters();
        activateSimilarSoundsModalsIfParameters();
    }
}

export { initializeStuffInContainer };