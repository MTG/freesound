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
import { initMap } from '../pages/map.js';
import { bindCollectionModals } from '../components/collections.js';


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

    bindConfirmationModalElements(container);  // Confirmation modals are also binded as they can work inside another modal

    // Bind other modals
    if (bindModals === true){
        bindDefaultModals(container);
        bindRemixGroupModals(container);
        bindBookmarkSoundModals(container);
        bindUserAnnotationsModal(container); 
        bindCollectionModals(container);
    }
    
    // Activate modals if needed (this should only be used the first time initializeStuffInContainer is called)
    if (activateModals === true){
        activateDefaultModalsIfParameters();
        activateUserAnnotationsModalIfParameters();
        activateRemixGroupModalsIfParameters();
    }

    // Init maps (note that already initialized maps won't be re-initialized)
    const maps = document.getElementsByClassName('map');
    maps.forEach(map => {
        const staticMapWrapper = document.getElementById('static_map_wrapper');
        const mapIsBehindStaticMap = staticMapWrapper !== null && staticMapWrapper.parentNode == map.parentNode;
        if (map.id !== 'static_map_wrapper' && !mapIsBehindStaticMap){
            // Only initialize non-static maps and maps which are not behind a static map (as those will be initialized when user clicks)
            initMap(map);
        }
    });
}

export { initializeStuffInContainer };