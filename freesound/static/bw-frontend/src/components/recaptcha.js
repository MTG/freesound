// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const initRecaptchaWidgets = () => {
    const recaptchaElements = document.getElementsByClassName('g-recaptcha');
    recaptchaElements.forEach(element => {
        try {
            // Wrap this call in try statement so that if recaptcha script has not loaded it does not stop execution
            const recaptchaKey = element.dataset.sitekey;
            // eslint-disable-next-line no-undef
            grecaptcha.render( element, {
                'sitekey' : recaptchaKey,
                'theme' : 'light',
            });
        } catch (e) {
            // Do nothing...
        }
    });
};

export default initRecaptchaWidgets;

// @license-end
