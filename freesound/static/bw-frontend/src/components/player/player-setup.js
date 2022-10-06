// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import {createPlayer} from "./player-ui";

const setupPlayers = () => {
  const players = [...document.getElementsByClassName('bw-player')]
  players.forEach(createPlayer)
}

setupPlayers()

// @license-end
