import {isScrolledIntoView} from "../utils/elementVisibility";
import debounce from 'lodash.debounce';

const scrollSpyElements = document.getElementsByClassName('scroll-spy');

const addClassToSpiedElement = () => {
    let elementToActivate = undefined;
    scrollSpyElements.forEach(linkElement => {
        const separatdParts = linkElement.href.split("#");
        const targetElementId = separatdParts[separatdParts.length - 1];
        const targetElement = document.getElementById(targetElementId);
        if (isScrolledIntoView(targetElement)){
            elementToActivate = linkElement;
        }
    });
    scrollSpyElements.forEach(linkElement => {
        if (linkElement == elementToActivate){
            linkElement.classList.add("bw-link--black");
        } else {
            linkElement.classList.remove("bw-link--black");
        }
    });
}

// Use a debouced function to save computation when doing smooth scrolls
const debouncedaddClassToSpiedElement = debounce(addClassToSpiedElement, 50, {'leading': false, 'maxWait': 200, 'trailing': true})

if (scrollSpyElements.length > 0){
    // If there are elements which should be "scroll spied", then add a global listener for them all
    debouncedaddClassToSpiedElement();
    addEventListener("scroll", () => {
        debouncedaddClassToSpiedElement();
    });
}