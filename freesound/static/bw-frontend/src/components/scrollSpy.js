import {isScrolledIntoView} from "../utils/elementVisible";

const scrollSpyElements = document.getElementsByClassName('scroll-spy');


const addClassToSipedElement = () => {
    let elementToActivate = undefined;
    scrollSpyElements.forEach(linkElement => {
        const separatdParts = linkElement.href.split("#");
        const targetElementId = separatdParts[separatdParts.length - 1];
        const targetElement = document.getElementById(targetElementId);
        console.log(targetElementId, isScrolledIntoView(targetElement));
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


if (scrollSpyElements.length > 0){
    // If there are elements which should be "scroll spied", then add a global listener for them all
    addClassToSipedElement();
    addEventListener("scroll", () => {
        addClassToSipedElement();
    });
}