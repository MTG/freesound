const addExplicitSoundWarnings = (container) => {
    const warningElements = container.getElementsByClassName('explicit-sound-blocker');
    warningElements.forEach(element => {
        const dismissButtonAnchor = element.getElementsByTagName('button')[0];
        dismissButtonAnchor.addEventListener('click', () =>{
            element.parentElement.getElementsByClassName('blur').forEach(blurredElement => {
                blurredElement.classList.remove('blur');
            });
            element.remove();
        });
    });
}

export {addExplicitSoundWarnings};