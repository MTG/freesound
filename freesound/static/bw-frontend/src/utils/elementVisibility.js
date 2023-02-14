// From: https://stackoverflow.com/questions/487073/how-to-check-if-element-is-visible-after-scrolling

export const isScrolledIntoView = el => {
    var rect = el.getBoundingClientRect();
    var elemTop = rect.top;
    var elemBottom = rect.bottom;
    return elemTop < window.innerHeight && elemBottom >= 0;
}
  