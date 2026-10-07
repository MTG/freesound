import { showToast } from './toast';
import { makePostRequest } from '../utils/postRequest';
import { dismissModal, activateModal } from './modal';
import { prepareCategoryFormFields } from './bstCategoryFormField';

// Generic wiring for inline "feedback experiment" boxes (see user_feedback). Nothing
// experiment-specific lives here: every box declares its own behaviour with data-
// attributes in its template, so a new experiment needs no changes to this file.

/* global userIsAuthenticated */

// View that returns the experiments of a page that loads them after the page loads.
const PAGE_ITEMS_URL = '/user-feedback/page-items/';

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

// Inputs shared by all the boxes of an experiment (e.g. info about the search).
// They are written once in the page in a [data-experiment-shared] element.
const collectSharedInputs = experimentId => {
  const shared = document.querySelector(
    `[data-experiment-shared="${experimentId}"]`
  );
  return shared ? collectNamedInputs(shared) : {};
};

// Boxes with [data-experiment-bar] are shown as a bar at the bottom of the page, with
// the styles of the toast. The bar is shown after [data-experiment-bar-delay] seconds.
const BAR_ANIMATION_DURATION_MS = 260;
const BAR_HIDE_AFTER_THANKS_MS = 3000;

const showBar = bar => {
  bar.style.display = 'block';
  // Force reflow so the show animation runs.
  void bar.offsetWidth;
  bar.classList.add('toast--visible');
};

const hideBar = bar => {
  bar.classList.remove('toast--visible');
  bar.classList.add('toast--hiding');
  setTimeout(() => {
    bar.classList.remove('toast--hiding');
    bar.style.display = 'none';
  }, BAR_ANIMATION_DURATION_MS);
};

const bindBar = bar => {
  const delay = Number(bar.dataset.experimentBarDelay || 0) * 1000;
  setTimeout(() => showBar(bar), delay);
  const closeButton = bar.querySelector('[data-experiment-bar-close]');
  if (closeButton) closeButton.addEventListener('click', () => hideBar(bar));
};

// One box: pick an answer (which may reveal extra fields), then Send posts it over
// AJAX. A box without a Send button is saved when an answer is clicked.
// Validation is left to the server, which replies with a JSON 400 we surface.
const bindFeedbackBox = box => {
  // Wire the two-level category picker if this experiment's box uses one.
  if (box.querySelector('.bst-category-field')) {
    prepareCategoryFormFields(box);
  }
  const isBar = box.hasAttribute('data-experiment-bar');
  if (isBar) bindBar(box);
  const expand = box.querySelector('[data-experiment-expand]');
  const answerButtons = [...box.querySelectorAll('[data-experiment-answer]')];
  const extras = [...box.querySelectorAll('[data-experiment-answer-extra]')];
  const sendButton = box.querySelector('[data-experiment-send]');
  // Name of the field where the answer is sent.
  const answerName = box.dataset.experimentAnswerName || 'answer';
  let chosenAnswer = null;
  let sending = false;

  const send = () => {
    if (!chosenAnswer || sending) return;
    // Disabled until the reply arrives (double-click cannot save twice).
    sending = true;
    if (sendButton) sendButton.disabled = true;
    makePostRequest(
      `${box.dataset.submitUrl}?ajax=1`,
      {
        ...collectSharedInputs(box.dataset.experimentId),
        ...collectNamedInputs(box),
        experiment_id: box.dataset.experimentId,
        [answerName]: chosenAnswer,
      },
      () => {
        box.innerHTML = `<b>${box.dataset.thanks || 'Thanks for your feedback!'}</b>`;
        // Hide the bar a bit after the thanks.
        if (isBar) setTimeout(() => hideBar(box), BAR_HIDE_AFTER_THANKS_MS);
      },
      responseText => {
        sending = false;
        if (sendButton) sendButton.disabled = false;
        showToast(
          firstFormError(responseText) ||
            'Something went wrong, please try again.'
        );
      }
    );
  };

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
      // No Send button, save now.
      if (!sendButton) send();
    });
  });

  if (sendButton) sendButton.addEventListener('click', send);
};

// "Don't ask again": AJAX opt-out so we can acknowledge and drop the box(es) without a
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
        // Remove all the boxes of the experiment from the page.
        document
          .querySelectorAll(`[data-experiment-id="${experimentId}"]`)
          .forEach(element => element.remove());
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

// Binds the elements only once, so it can be called again after more boxes are added to the page.
const bindOnce = (selector, bind) =>
  [...document.querySelectorAll(selector)].forEach(element => {
    if (element.dataset.experimentBound) return;
    element.dataset.experimentBound = '1';
    bind(element);
  });

const prepareFeedbackExperiments = () => {
  bindOnce('[data-experiment-box]', bindFeedbackBox);
  bindOnce('form[data-experiment-optout]', bindOptOut);
  bindOnce('[data-info-modal]', bindInfoButton);
};

// Places a piece of HTML in the page. With a target, it goes right after the block that
// has the target element inside its container. Without a target, at the end of the page.
const placePageItem = item => {
  if (!item.target) {
    document.body.insertAdjacentHTML('beforeend', item.html);
    return;
  }
  const target = document.querySelector(item.target);
  const container = target && target.closest(item.container);
  if (!container) return;
  let block = target;
  while (block.parentElement !== container) block = block.parentElement;
  block.insertAdjacentHTML('afterend', item.html);
};

// Loads the experiments of a page that does not have them in its template. The server gets
// the parameters of the page and the sounds shown in it, and returns the HTML to place.
const loadFeedbackExperiments = () => {
  if (!userIsAuthenticated) return;
  const soundIds = [...document.querySelectorAll('[data-sound-id]')].map(
    element => element.dataset.soundId
  );
  const params = new URLSearchParams(window.location.search);
  params.set('experiment_path', window.location.pathname);
  params.set('experiment_sound_ids', [...new Set(soundIds)].join(','));
  fetch(`${PAGE_ITEMS_URL}?${params}`)
    .then(response => response.json())
    .then(data => {
      data.items.forEach(placePageItem);
      prepareFeedbackExperiments();
    })
    .catch(() => {
      // The page works the same without the experiments.
    });
};

export { prepareFeedbackExperiments, loadFeedbackExperiments };
