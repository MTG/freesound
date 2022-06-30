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
