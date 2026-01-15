export default function wait(milliseconds) {
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}
