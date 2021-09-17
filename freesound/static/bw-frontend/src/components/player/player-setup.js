import {createPlayer} from "./player-ui";

const setupPlayers = () => {
  const players = [...document.getElementsByClassName('bw-player')]
  players.forEach(createPlayer)
}

setupPlayers()

