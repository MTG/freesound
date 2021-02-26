const initRecaptchaWidgets = () => {
    const recaptchaElements = document.getElementsByClassName('g-recaptcha');
    recaptchaElements.forEach(element => {
        const recaptchaKey = element.dataset.sitekey;
        // eslint-disable-next-line no-undef
        grecaptcha.render( element, {
            'sitekey' : recaptchaKey,
            'theme' : 'light',
        });
    });
};

export default initRecaptchaWidgets;
