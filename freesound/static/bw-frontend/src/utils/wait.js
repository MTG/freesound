// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

export default function wait(milliseconds) {
  return new Promise(resolve => setTimeout(resolve, milliseconds))
}

// @license-end
