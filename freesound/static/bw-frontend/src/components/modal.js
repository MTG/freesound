import {showToast, showToastNoTimeout, dismissToast} from "./toast";
import {initializePlayersInContainer, stopAllPlayersInContainer} from './player/utils';
import {initializeCarousels} from './carousel';
import {initRatingWidgets} from './rating';
import serialize from '../utils/formSerializer'

const bwPageElement = document.getElementsByClassName('bw-page')[0];

// Util functions to initialize/stop players and other stuff that could usually be found in modals with sound players
const initPlayersInModal = (modalContainer) => {
  initializePlayersInContainer(modalContainer);
  initRatingWidgets(modalContainer);
  initializeCarousels(modalContainer);
}

const stopPlayersInModal = (modalContainer) => {
  stopAllPlayersInContainer(modalContainer);
}

// Util function to bind modal activation elements
const bindModalActivationElements = (querySelectorStr, handleModalFunction, container) => {
  if (container === undefined){ container = document; }
  container.querySelectorAll(querySelectorStr).forEach(element => {
    if (element.dataset.alreadyBinded !== undefined){ return; }
    element.dataset.alreadyBinded = true;
    element.addEventListener('click', (evt) => {
      evt.preventDefault();
      handleModalFunction(element.dataset.modalContentUrl, element.dataset.modalActivationParam);
    });
  });
}

// Util function to activate modals with parameters
const activateModalsIfParameters = (querySelectorStr, handleModalFunction) => {
  const urlParams = new URLSearchParams(window.location.search);
  for (const element of [...document.querySelectorAll(querySelectorStr)]) {
    const activationParam = element.dataset.modalActivationParam;
    const paramValue = urlParams.get(activationParam);
    if (paramValue) {
      handleModalFunction(element.dataset.modalContentUrl, activationParam, paramValue);
      break;  // Only open one modal (the first found with an activated parameter)
    }
  }
}

// Function to make modals visible
const activateModal = modalContainerId => {
  const modalContainer = document.getElementById(modalContainerId);
  if (modalContainer !== null){
    modalContainer.classList.add('show');
    modalContainer.style.display = 'block';
    modalContainer.setAttribute('aria-hidden', 'false');
    bwPageElement.setAttribute('aria-hidden', 'true');
    initModalDismissButton(modalContainer);
    modalContainer.focus()
  }
};

// Util functions to dismiss a modal
const dismissModal = modalContainerId => {
  const modalContainer = document.getElementById(modalContainerId);
  if (modalContainer !== null){
    modalContainer.classList.remove('show');
    modalContainer.style.display = 'none';
    modalContainer.setAttribute('aria-hidden', 'true');
    bwPageElement.setAttribute('aria-hidden', 'false');
    modalContainer.blur()
  }
};

const initModalDismissButton = (modalContainerElement) => {
  const modalDismiss = [...modalContainerElement.querySelectorAll('[data-dismiss="modal"]')];
  modalDismiss.forEach(dismiss => {
    dismiss.addEventListener('click', () => dismissModal(modalContainerElement.id));
  });
}

// Confirmation modal logic
const confirmationModalButtons = [...document.querySelectorAll('[data-toggle="confirmation-modal"]')];
confirmationModalButtons.forEach(modalButton => {
  modalButton.addEventListener('click', () => {
    const confirmationModalTitle = document.getElementById('confirmationModalTitle');
    confirmationModalTitle.innerText = modalButton.dataset.modalConfirmationTitle;
    const confirmationModalHelpText = document.getElementById('confirmationModalHelpText');
    const helpText = modalButton.dataset.modalConfirmationHelpText;
    if (helpText !== undefined){
      confirmationModalHelpText.innerText = helpText;
    } else {
      confirmationModalHelpText.innerText = '';
    }
    const confirmationModalAcceptForm = document.getElementById('confirmationModalAcceptSubmitForm');
    confirmationModalAcceptForm.action = modalButton.dataset.modalConfirmationUrl;
    handleModal('confirmationModal');
  });
});

// Generic modals logic
const genericModalWrapper = document.getElementById('genericModalWrapper');

const handleGenericModal = (fetchContentUrl, onLoadedCallback, onClosedCallback, doRequestAsync, showLoadingToast, modalActivationParam) => {
  if (showLoadingToast !== false) { showToastNoTimeout('Loading...'); }
  const req = new XMLHttpRequest();
  req.open('GET', fetchContentUrl, doRequestAsync !== false);
  req.onload = () => {
    if (req.status >= 200 && req.status < 300) {
      if (req.responseText !== ""){
        // If response contents are not empty, add modal contents to the generic modal wrapper (the requested URL
        // should return a modal template extending "modal_base.html")
        genericModalWrapper.innerHTML = req.responseText;
        const modalContainerId = genericModalWrapper.getElementsByClassName('modal')[0].id;
        const modalContainer = document.getElementById(modalContainerId);
        
        // Make modal visible
        modalContainer.classList.add('show');
        modalContainer.style.display = 'block';
        
        // Add dismiss click handler including call to callback if defined
        const modalDismiss = [...document.querySelectorAll('[data-dismiss="modal"]')];
        modalDismiss.forEach(dismiss => {
          dismiss.addEventListener('click', () => {
            dismissModal(modalContainerId);
            if (onClosedCallback !== undefined){
              onClosedCallback(modalContainer);
            }
            // If modal is activated with a param, remove the param to the URL when closing the modal
            if (modalActivationParam !== undefined) {
              const searchParams = new URLSearchParams(window.location.search);
              searchParams.delete(modalActivationParam);
              const url = window.location.protocol + '//' + window.location.host + window.location.pathname + '?' + searchParams.toString();
              window.history.replaceState(null, "", url);
            }
          });
        });
        
        // Make paginator update modal (if any)
        modalContainer.getElementsByClassName('bw-pagination_container').forEach(paginationContainer => {
          paginationContainer.getElementsByTagName('a').forEach(paginatorLinkElement => {
            const loadPageUrl = paginatorLinkElement.href;
            paginatorLinkElement.href = 'javascript:void(0);';
            paginatorLinkElement.onclick = () => {
              handleGenericModal(loadPageUrl, onLoadedCallback, onClosedCallback, doRequestAsync, showLoadingToast, modalActivationParam);
            };
          });
        });
        
        // Dismiss loading indicator toast and call "on loaded" call back
        if (showLoadingToast !== false) { dismissToast(); }
        if (onLoadedCallback !== undefined){
          onLoadedCallback(modalContainer);
        }
        
        // If modal is activated with a param, add the param to the URL when opening the modal
        if (modalActivationParam !== undefined){
          const modalAjaxRequestSearchParams = new URLSearchParams(fetchContentUrl);
          const currentPage = modalAjaxRequestSearchParams.get('page') || '1';
          const searchParams = new URLSearchParams(window.location.search);
          searchParams.set(modalActivationParam, currentPage);
          const url = window.location.protocol + '//' + window.location.host + window.location.pathname + '?' + searchParams.toString();
          window.history.replaceState(null, "", url);
        }
      } else {
        // If response contents are empty, do not show any modal but dismiss the loading toast (if used)
        if (showLoadingToast !== false) { dismissToast(); }
      }
    } else {
      // Unexpected errors happened while processing request: close modal and show error in toast
      showToast('Unexpected errors occurred while loading the requested content. Please try again later...')
    }
  };
  req.onerror = () => {
    // Unexpected errors happened while processing request: close modal and show error in toast
    showToast('Unexpected errors occurred while loading the requested content. Please try again later...')
  };
  
  // Send the form
  req.send();
};


const handleGenericModalWithForm = (fetchContentUrl, onLoadedCallback, onClosedCallback, onFormSubmissionSucceeded, onFormSubmissionError, doRequestAsync, showLoadingToast, modalActivationParam) => {
  // This version of the generic modal is useful for modal contents that contain forms which, upon submission, will return HTML content if there were form errors
  // which should be used to replace the current contents of the form, and will return a JSON response if the form validated correctly in the backend. That JSON
  // response could include some relevant data or no data at all, but is used to differentiate from the HTML response
  
  const genericModalWithFormCustomSubmit = (evt) => {
    
    // Create new XMLHttpRequest request to submit form contents
    const form = evt.target;
    const params = serialize(form);
    const req = new XMLHttpRequest();
    req.open('POST', form.action, true);
    req.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
    
    req.onload = () => {
      if (req.status >= 200 && req.status < 300) {
        if (req.getResponseHeader('content-type') === 'application/json'){
          // If response is of type JSON, that means the form was submitted and validated successfully, show toast and close modal
          const modalContainerId = genericModalWrapper.getElementsByClassName('modal')[0].id;
          dismissModal(modalContainerId);
          if (onFormSubmissionSucceeded !== undefined){
            onFormSubmissionSucceeded(req);
          }
        }  else {
          // If the response is not JSON, that means the response are the HTML elements of the
          // form (including error warnings) and we should replace current modal HTML with this one
          // and re-run any needed modal initialization
          genericModalWrapper.innerHTML = req.responseText;
          const modalContainerId = genericModalWrapper.getElementsByClassName('modal')[0].id;
          const modalContainer = document.getElementById(modalContainerId);
          modalContainer.classList.add('show');
          modalContainer.style.display = 'block';
          
          // Re-run modal initialization
          const form = modalContainer.getElementsByTagName('form')[0];
          if (onLoadedCallback !== undefined){
            onLoadedCallback(modalContainer);
          }
          form.onsubmit = genericModalWithFormCustomSubmit
          
          // Re-bind dismiss modal buttons
          const modalDismiss = genericModalWrapper.querySelectorAll('[data-dismiss="modal"]');
          modalDismiss.forEach(dismiss => {
            dismiss.addEventListener('click', () => {
              dismissModal(modalContainerId);
              if (onClosedCallback !== undefined){
                onClosedCallback(modalContainer);
              }
            });
          });
        }
      }
    };
    
    req.onerror = () => {
      // Unexpected errors happened while processing request: close modal and show error in toast
      const modalContainerId = genericModalWrapper.getElementsByClassName('modal')[0].id;
      dismissModal(modalContainerId);
      if (onFormSubmissionError !== undefined){
        onFormSubmissionError(req);
      } else {
        showToast("Unexpected errors occurred while processing the form, pelase try again later...")
      }
    };
    
    // Send the request with form data
    req.send(params);
    
    // Return false so default submission does not happen
    return false;
  }
  
  handleGenericModal(fetchContentUrl, (modalContainer) => {
    if (onLoadedCallback !== undefined){
      onLoadedCallback(modalContainer);
    }
    const form = modalContainer.getElementsByTagName('form')[0];
    form.onsubmit = genericModalWithFormCustomSubmit
  }, onClosedCallback, doRequestAsync, showLoadingToast, modalActivationParam)
}

export {activateModal, dismissModal, handleGenericModal, handleGenericModalWithForm, bindModalActivationElements, activateModalsIfParameters, initPlayersInModal, stopPlayersInModal};
