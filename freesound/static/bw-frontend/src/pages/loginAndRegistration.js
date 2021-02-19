import './page-polyfills';
import {handleDismissModal, handleModal} from "../components/modal";


const modalLinks = [
    document.querySelectorAll('[data-link="forgottenPasswordModal"]'),
    document.querySelectorAll('[data-link="registerModal"]'),
    document.querySelectorAll('[data-link="loginModal"]'),
];

modalLinks.forEach(links => {
    links.forEach(link => {
        link.addEventListener('click', () => {
            handleDismissModal(link.dataset.link);
            handleModal(link.dataset.link);
        });
    });
});