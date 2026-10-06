import { showToast } from './toast';
import { makePostRequest } from '../utils/postRequest';
import { dismissModal, activateModal } from './modal';
import { prepareCategoryFormFields } from './bstCategoryFormField';

// Generic wiring for inline "feedback experiment" boxes (see user_feedback). Nothing
// experiment-specific lives here: every box declares its own behaviour with data-
// attributes in its template, so a new experiment needs no changes to this file.

// First field-error message out of the submit view's JSON 400 body.
const firstFormError = responseText => {
  try {
    const errors = JSON.parse(responseText).errors || {};
    const firstField = Object.keys(errors)[0];
    return firstField ? errors[firstField][0].message : null;
  } catch {
    return null;
  }
};

// Every named input inside an element, as a plain {name: value} object.
const collectNamedInputs = root =>
  [...root.querySelectorAll('[name]')].reduce((data, input) => {
    data[input.name] = input.value;
    return data;
  }, {});

// One box: pick an answer (which may reveal extra fields), then Send posts it over
// AJAX. Validation is left to the server, which replies with a JSON 400 we surface.
const bindFeedbackBox = box => {
  // Wire the two-level category picker if this experiment's box uses one.
  if (box.querySelector('.bst-category-field')) {
    prepareCategoryFormFields(box);
  }
  const expand = box.querySelector('[data-experiment-expand]');
  const answerButtons = [...box.querySelectorAll('[data-experiment-answer]')];
  const extras = [...box.querySelectorAll('[data-experiment-answer-extra]')];
  let chosenAnswer = null;

  answerButtons.forEach(button => {
    button.addEventListener('click', () => {
      chosenAnswer = button.dataset.experimentAnswer;
      // Highlight the chosen answer; keep the others outlined so the choice can change.
      answerButtons.forEach(other => {
        other.classList.toggle('btn-primary', other === button);
        other.classList.toggle('btn-inverse', other !== button);
      });
      if (expand) expand.style.display = '';
      // Reveal only the extras tied to this answer (e.g. the "no" category picker).
      extras.forEach(extra => {
        extra.style.display =
          extra.dataset.experimentAnswerExtra === chosenAnswer ? '' : 'none';
      });
    });
  });

  const sendButton = box.querySelector('[data-experiment-send]');
  if (sendButton) {
    sendButton.addEventListener('click', () => {
      if (!chosenAnswer) return;
      makePostRequest(
        `${box.dataset.submitUrl}?ajax=1`,
        {
          ...collectNamedInputs(box),
          experiment_id: box.dataset.experimentId,
          answer: chosenAnswer,
        },
        () => {
          box.innerHTML = `<b>${box.dataset.thanks || 'Thanks for your feedback!'}</b>`;
        },
        responseText =>
          showToast(
            firstFormError(responseText) ||
              'Something went wrong, please try again.'
          )
      );
    });
  }
};

// "Don't ask again": AJAX opt-out so we can acknowledge and drop the box without a
// reload. Falls back to a plain POST + redirect if this JS never runs.
const bindOptOut = form => {
  form.addEventListener('submit', event => {
    event.preventDefault();
    const experimentId = form.querySelector('[name="experiment_id"]').value;
    makePostRequest(
      `${form.action}?ajax=1`,
      { experiment_id: experimentId },
      () => {
        if (form.dataset.dismissModal) dismissModal(form.dataset.dismissModal);
        const box = document.querySelector(
          `[data-experiment-box][data-experiment-id="${experimentId}"]`
        );
        if (box) box.remove();
        showToast("Got it, we won't ask you this again.");
      },
      () => showToast('Something went wrong, please try again.')
    );
  });
};

// Buttons that open an experiment's self-contained info modal already in the DOM.
const bindInfoButton = button =>
  button.addEventListener('click', () =>
    activateModal(button.dataset.infoModal)
  );

const prepareFeedbackExperiments = () => {
  [...document.querySelectorAll('[data-experiment-box]')].forEach(
    bindFeedbackBox
  );
  [...document.querySelectorAll('form[data-experiment-optout]')].forEach(
    bindOptOut
  );
  [...document.querySelectorAll('[data-info-modal]')].forEach(bindInfoButton);
};

export { prepareFeedbackExperiments };
