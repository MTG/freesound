// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const warningElements = document.getElementsByClassName('explicit-sound-blocker');

warningElements.forEach(element => {
    const dismissButtonAnchor = element.getElementsByTagName('button')[0];
    dismissButtonAnchor.addEventListener('click', () =>{
        element.parentElement.getElementsByClassName('blur').forEach(blurredElement => {
           blurredElement.classList.remove('blur');
        });
        element.remove();
    });
});

// @license-end
