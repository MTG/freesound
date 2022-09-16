import debounce from 'lodash.debounce'

/**
 * @param {{ label: string, value: string, id?: number }} suggestion
 * @param {HTMLDivElement} optionsWrapper
 * @param {HTMLDivElement} input
 */
export const showSuggestion = (suggestion, optionsWrapper, input) => {
  const suggestionWrapper = document.createElement('div')
  suggestionWrapper.classList.add('input-typeahead-suggestion-wrapper')
  suggestionWrapper.innerHTML = suggestion.label
  suggestionWrapper.addEventListener('click', evt => {
    optionsWrapper.classList.add('hidden')
    input.value = suggestion.value
    input.blur()
    input.form.submit()  // Submit the form so query is executed
  })

  optionsWrapper.appendChild(suggestionWrapper)
}

/**
 * @param {HTMLDivElement} optionsWrapper
 */
export const clearSuggestions = optionsWrapper => {
  optionsWrapper.innerHTML = ''
}

/**
 * @param {HTMLInputElement} input
 * @param {(value: string) => Promise<Array<{ label: string, id: number }>>} onChange:
 */
export const addTypeAheadFeatures = (
  input,
  onChange = () => Promise.resolve([])
) => {
  if (input.dataset.typeahead !== 'true') return
  let suggestions = []
  let focusedOptionIndex = -1
  const wrapper = input.parentElement.parentElement
  const optionsWrapper = document.createElement('div')
  optionsWrapper.classList.add('input-typeahead-suggestions', 'hidden')
  wrapper.appendChild(optionsWrapper)
  const debouncedOnChange = debounce(onChange, 100)
  input.addEventListener('input', async evt => {
    suggestions = (await debouncedOnChange(evt.target.value)) || []
    clearSuggestions(optionsWrapper)
    focusedOptionIndex = -1
    suggestions.forEach(suggestion =>
      showSuggestion(suggestion, optionsWrapper, input)
    )
  })

  const updateFocusedOption = () => {
    const allOptions = [
      ...optionsWrapper.getElementsByClassName(
        'input-typeahead-suggestion-wrapper'
      ),
    ]
    allOptions.forEach(option => option.classList.remove('active'))
    if (focusedOptionIndex >= 0 && allOptions[focusedOptionIndex]) {
      const selectedOption = allOptions[focusedOptionIndex]
      selectedOption.classList.add('active')
      try {
        selectedOption.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      } catch (e) {
        selectedOption.scrollIntoView(true)
      }
    }
  }

  input.addEventListener('focus', () => {
    optionsWrapper.classList.remove('hidden')
  })
  input.addEventListener('blur', () => {
    // Use a timeout here so if blur is triggered because we clicked one of the suggestions, it has time
    // to tigger the suggestion's click event before hidden is applied (that would prevent click event from
    // triggering)
    setTimeout(() => {
      optionsWrapper.classList.add('hidden')
    }, 200);
  })
  input.addEventListener('keydown', evt => {
    const DOWN_ARROW = 40
    const UP_ARROW = 38
    const ENTER_KEY = 13
    if (evt.keyCode === DOWN_ARROW) {
      evt.preventDefault()
      focusedOptionIndex = Math.min(
        focusedOptionIndex + 1,
        suggestions.length - 1
      )
      updateFocusedOption()
    } else if (evt.keyCode === UP_ARROW) {
      evt.preventDefault()
      focusedOptionIndex = Math.max(-1, focusedOptionIndex - 1)
      updateFocusedOption()
    } else if (evt.keyCode === ENTER_KEY && focusedOptionIndex >= 0) {
      evt.preventDefault()
      input.value = suggestions[focusedOptionIndex].value
      input.blur()
      input.form.submit()  // Submit the form so query is executed
    }
  })
}
