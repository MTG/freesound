/**
 * @param {{ label: string, value: string, id?: number }} suggestion
 * @param {HTMLDivElement} optionsWrapper
 * @param {HTMLDivElement} input
 */
export const showSuggestion = (
  suggestion,
  optionsWrapper,
  input,
  onSuggestionSelectedCallback
) => {
  const suggestionWrapper = document.createElement('div');
  suggestionWrapper.classList.add('input-typeahead-suggestion-wrapper');
  suggestionWrapper.innerHTML = suggestion.label;
  suggestionWrapper.addEventListener('click', evt => {
    evt.preventDefault();
    onSuggestionSelectedCallback(suggestion, optionsWrapper, input);
  });
  optionsWrapper.appendChild(suggestionWrapper);
};

/**
 * @param {HTMLDivElement} optionsWrapper
 */
export const clearSuggestions = optionsWrapper => {
  optionsWrapper.innerHTML = '';
};

/**
 * @param {HTMLInputElement} input
 * @param {(value: string) => Promise<Array<{ label: string, id: number }>>} onChange:
 * @param onSuggestionSelectedCallback
 * @param wrapperElement
 */
export const addTypeAheadFeatures = (
  input,
  onChange = () => Promise.resolve([]),
  onSuggestionSelectedCallback,
  wrapperElement // Where to "attatch" the dropdown
) => {
  if (input.dataset.typeahead !== 'true') return;
  let suggestions = [];
  let focusedOptionIndex = -1;
  let wrapper;
  if (wrapperElement === undefined) {
    // By default, wrapper is taken as 2 parent nodes above
    wrapper = input.parentElement.parentElement;
  } else {
    wrapper = wrapperElement;
  }
  const optionsWrapper = document.createElement('div');
  optionsWrapper.classList.add('input-typeahead-suggestions', 'hidden');
  wrapper.appendChild(optionsWrapper);

  const eventTypes = ['input', 'focus'];
  eventTypes.forEach(eventType => {
    input.addEventListener(eventType, async evt => {
      suggestions = (await onChange(evt.target)) || []; // Pass input element to "get suggestions" function
      clearSuggestions(optionsWrapper);
      focusedOptionIndex = -1;
      suggestions.forEach(suggestion => {
        showSuggestion(
          suggestion,
          optionsWrapper,
          input,
          onSuggestionSelectedCallback
        );
      });
      if (suggestions.length > 0) {
        optionsWrapper.classList.remove('hidden');
      } else {
        optionsWrapper.classList.add('hidden');
      }
    });
  });

  const updateFocusedOption = () => {
    const allOptions = [
      ...optionsWrapper.getElementsByClassName(
        'input-typeahead-suggestion-wrapper'
      ),
    ];
    allOptions.forEach(option => option.classList.remove('active'));
    if (focusedOptionIndex >= 0 && allOptions[focusedOptionIndex]) {
      const selectedOption = allOptions[focusedOptionIndex];
      selectedOption.classList.add('active');
      try {
        selectedOption.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } catch (e) {
        selectedOption.scrollIntoView(true);
      }
    }
  };

  input.addEventListener('blur', () => {
    // Use a timeout here so if blur is triggered because we clicked one of the suggestions, it has time
    // to tigger the suggestion's click event before hidden is applied (that would prevent click event from
    // triggering)
    setTimeout(() => {
      optionsWrapper.classList.add('hidden');
    }, 200);
  });
  input.addEventListener('keydown', evt => {
    const DOWN_ARROW = 40;
    const UP_ARROW = 38;
    const ENTER_KEY = 13;
    if (evt.keyCode === DOWN_ARROW) {
      evt.preventDefault();
      focusedOptionIndex = Math.min(
        focusedOptionIndex + 1,
        suggestions.length - 1
      );
      updateFocusedOption();
    } else if (evt.keyCode === UP_ARROW) {
      evt.preventDefault();
      focusedOptionIndex = Math.max(-1, focusedOptionIndex - 1);
      updateFocusedOption();
    } else if (evt.keyCode === ENTER_KEY && focusedOptionIndex >= 0) {
      evt.preventDefault();
      onSuggestionSelectedCallback(
        suggestions[focusedOptionIndex],
        optionsWrapper,
        input
      );
    }
  });
};
