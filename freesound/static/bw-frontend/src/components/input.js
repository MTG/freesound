// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import { createIconElement } from '../utils/icons'

const searchBoxes = [...document.querySelectorAll('input[type="search"]')]

searchBoxes.forEach(searchField => {
  const inputWrapper = searchField.parentNode
  const searchIconNode = createIconElement('bw-icon-search')
  searchIconNode.classList.add('input-icon')
  inputWrapper.insertBefore(searchIconNode, searchField)
})

// @license-end
