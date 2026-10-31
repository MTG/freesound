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

// Inputs shared by all the boxes of an experiment (e.g. info about the search).
// They are written once in the page in a [data-experiment-shared] element.
const collectSharedInputs = experimentId => {
  const shared = document.querySelector(
    `[data-experiment-shared="${experimentId}"]`
  );
  return shared ? collectNamedInputs(shared) : {};
};

// Sounds played in the page, when each was first played, and how many times.
const playedSounds = new Map();
const playCallbacks = [];
const secondsInPage = () => Math.round(performance.now() / 1000);

let trackingPlays = false;
const trackPlays = () => {
  if (trackingPlays) return;
  trackingPlays = true;
  document.addEventListener(
    'play',
    event => {
      const player = event.target.closest('[data-sound-id]');
      if (!player) return;
      const soundId = player.dataset.soundId;
      const sound = playedSounds.get(soundId);
      if (sound) {
        sound.times += 1;
        return;
      }
      playedSounds.set(soundId, { seconds: secondsInPage(), times: 1 });
      playCallbacks.forEach(callback => callback());
    },
    true
  );
};

// Fills in the fields about the plays before an answer is sent.
const fillPlayInputs = () => {
  const fill = (selector, value) =>
    document.querySelectorAll(selector).forEach(input => {
      input.value = value;
    });
  fill(
    '[data-experiment-played-sounds]',
    [...playedSounds]
      .map(([id, sound]) => `${id}:${sound.seconds}:${sound.times}`)
      .join(',')
  );
  fill('[data-experiment-seconds-in-page]', secondsInPage());
};

// Runs the callback Y seconds after X different sounds are played in the page.
const afterPlays = (element, callback) => {
  const plays = Number(element.dataset.experimentPlays || 0);
  const delay = Number(element.dataset.experimentDelay || 0) * 1000;
  let waiting = true;
  const runIfEnoughPlays = () => {
    if (!waiting || playedSounds.size < plays) return;
    waiting = false;
    setTimeout(callback, delay);
  };
  playCallbacks.push(runIfEnoughPlays);
  runIfEnoughPlays();
};

// Shows a box when its sound is played, or when enough sounds are played.
const bindShowOnPlay = box => {
  const soundId = box.dataset.experimentShowOnPlay;
  const show = () => {
    box.style.display = '';
  };
  const showIfPlayed = () => {
    if (playedSounds.has(soundId)) show();
  };
  playCallbacks.push(showIfPlayed);
  showIfPlayed();
  // afterPlays(box, show);  // Do not show all "was this useful" quesions after X plays from other sounds, only after a sound is played
};

// Boxes with [data-experiment-bar] are shown as a bar at the bottom of the page, with
// the styles of the toast. The bar waits for the plays and the delay of afterPlays.
const BAR_ANIMATION_DURATION_MS = 260;
const HIDE_AFTER_THANKS_MS = 3000;

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

// Fades a box out and collapses its height, then removes it.
const removeBox = box => {
  // Start from the current height so max-height can transition to 0.
  box.style.maxHeight = `${box.scrollHeight}px`;
  void box.offsetWidth;
  box.classList.add('experiment-box--hiding');
  // Hidden boxes never fire transitionend, so also remove them after a timeout.
  setTimeout(() => box.remove(), BAR_ANIMATION_DURATION_MS + 100);
};

// A box with [data-experiment-closes-boxes] removes the other boxes of its experiment.
const closeOtherBoxes = box => {
  if (!box.hasAttribute('data-experiment-closes-boxes')) return;
  document
    .querySelectorAll(
      `[data-experiment-box][data-experiment-id="${box.dataset.experimentId}"]`
    )
    .forEach(other => other !== box && removeBox(other));
};

const bindBar = bar => {
  afterPlays(bar, () => showBar(bar));
  const closeButton = bar.querySelector('[data-experiment-bar-close]');
  if (closeButton)
    closeButton.addEventListener('click', () => {
      hideBar(bar);
      closeOtherBoxes(bar);
    });
};

// Boxes with [data-experiment-place-after] are moved right after the sound with that id, inside the
// element of the page that wraps the sound ([data-experiment-place-in]). Without it, they are removed.
// Returns whether the box was placed.
const placeAfterSound = box => {
  const sound = document.querySelector(
    `[data-sound-id="${box.dataset.experimentPlaceAfter}"]`
  );
  const container = sound && sound.closest(box.dataset.experimentPlaceIn);
  if (!container) {
    box.remove();
    return false;
  }
  let block = sound;
  while (block.parentElement !== container) block = block.parentElement;
  block.insertAdjacentElement('afterend', box);
  return true;
};

// One box: pick an answer (which may reveal extra fields), then Send posts it over
// AJAX. A box without a Send button is saved when an answer is clicked.
// Validation is left to the server, which replies with a JSON 400 we surface.
const bindFeedbackBox = box => {
  if (box.dataset.experimentPlaceAfter && !placeAfterSound(box)) return;
  // Wire the two-level category picker if this experiment's box uses one.
  if (box.querySelector('.bst-category-field')) {
    prepareCategoryFormFields(box);
  }
  const isBar = box.hasAttribute('data-experiment-bar');
  if (isBar) bindBar(box);
  if (box.dataset.experimentShowOnPlay) bindShowOnPlay(box);
  const expand = box.querySelector('[data-experiment-expand]');
  const answerButtons = [...box.querySelectorAll('[data-experiment-answer]')];
  const extras = [...box.querySelectorAll('[data-experiment-answer-extra]')];
  const sendButton = box.querySelector('[data-experiment-send]');
  // Name of the field where the answer is sent.
  const answerName = box.dataset.experimentAnswerName || 'answer';
  let chosenAnswer = null;
  let sending = false;

  // Click out of the bar to minimize it, click in to open it.
  if (isBar && expand) {
    document.addEventListener('click', event => {
      if (!box.contains(event.target)) expand.style.display = 'none';
      else if (chosenAnswer) expand.style.display = '';
    });
  }

  const send = () => {
    if (!chosenAnswer || sending) return;
    // Disabled until the reply arrives (double-click cannot save twice).
    sending = true;
    if (sendButton) sendButton.disabled = true;
    fillPlayInputs();
    makePostRequest(
      `${box.dataset.submitUrl}?ajax=1`,
      {
        ...collectSharedInputs(box.dataset.experimentId),
        ...collectNamedInputs(box),
        experiment_id: box.dataset.experimentId,
        [answerName]: chosenAnswer,
      },
      () => {
        box.innerHTML = `${box.dataset.thanks || 'Thanks for your feedback!'}`;
        // Hide the answered bar and boxes a bit after the thanks.
        if (isBar) setTimeout(() => hideBar(box), HIDE_AFTER_THANKS_MS);
        else if (box.hasAttribute('data-experiment-hide-after-thanks'))
          setTimeout(() => removeBox(box), HIDE_AFTER_THANKS_MS);
        //setTimeout(() => closeOtherBoxes(box), HIDE_AFTER_THANKS_MS);  // No need to close individual sound boxes after the general feedback is provided
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
      // Not needed without a Send button, because the answer is saved right away.
      if (sendButton) {
        answerButtons.forEach(other => {
          other.classList.toggle('btn-primary', other === button);
          other.classList.toggle('btn-inverse', other !== button);
        });
      }
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

const bindFeedbackExperimentBoxes = () => {
  trackPlays();
  bindOnce('[data-experiment-box]', bindFeedbackBox);
  bindOnce('form[data-experiment-optout]', bindOptOut);
  bindOnce('[data-info-modal]', bindInfoButton);
};

export { bindFeedbackExperimentBoxes };
