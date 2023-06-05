import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters, initPlayersInModal, stopPlayersInModal} from './modal';

const drawArrows =() => {
    const arrowsPanel = document.getElementsByClassName('remix-group-arrows-panel')[0];
    const soundsPanel = document.getElementsByClassName('remix-group-sounds-panel')[0];
    const data = JSON.parse(arrowsPanel.dataset.remixGroupData);
    let svgContent = '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">\
    <defs>\
        <marker id="arrowhead" viewBox="0 0 10 10" refX="3" refY="5"\
            markerWidth="6" markerHeight="6" orient="auto">\
        <path d="M 0 0 L 10 5 L 0 10 z" />\
        </marker>\
    </defs>\
    <g marker-end="url(#arrowhead)">';
    const links = data.links;
    const maxLinkLength = Math.max(...links.map(x => Math.abs(x.target - x.source))) ;
    links.forEach(link => {
        const sourceSoundDiv = soundsPanel.children[link.source];
        const targetSoundDiv = soundsPanel.children[link.target];
        const posStart = {
            x: arrowsPanel.offsetWidth - 50,
            y: sourceSoundDiv.offsetTop  + sourceSoundDiv.offsetHeight / 2
        };
        const posEnd = {
            x: arrowsPanel.offsetWidth - 50,
            y: targetSoundDiv.offsetTop  + targetSoundDiv.offsetHeight / 2
        };
        const linkLength = Math.abs(link.target - link.source);
        const eccentricity = arrowsPanel.offsetWidth * linkLength / maxLinkLength * 1.1;
        const dStr =
            "M" +
            (posStart.x      ) + "," + (posStart.y) + " " +
            "C" +
            (posStart.x - eccentricity) + "," + (posStart.y) + " " +
            (posEnd.x - eccentricity) + "," + (posEnd.y) + " " +
            (posEnd.x      ) + "," + (posEnd.y);
        svgContent += `\n<path d="${dStr}"></path>`;
    });
    arrowsPanel.innerHTML = svgContent + '</g></svg>';
}

const onResize = (evt) => {
    drawArrows();
}

const handleRemixGroupsModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, (modalContainer) => {
        initPlayersInModal(modalContainer);
        drawArrows();
        window.addEventListener("resize", onResize);
    }, (modalContainer) => {
        stopPlayersInModal(modalContainer);
        window.removeEventListener("resize", onResize);
    }, true, true, modalActivationParam);
}

const bindRemixGroupModals = (container) => {
    bindModalActivationElements('[data-toggle="remix-group-modal"]', handleRemixGroupsModal, container);
}

bindRemixGroupModals();
activateModalsIfParameters('[data-toggle="remix-group-modal"]', handleRemixGroupsModal);

export {bindRemixGroupModals};
