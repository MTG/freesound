import { getCookie, setCookie } from "../utils/cookies";
import { showToastNoTimeout, dismissToast } from "./toast";

const cookieConsentValue = getCookie("cookieConsent");
if (cookieConsentValue !== "yes") {
    showToastNoTimeout('<div class="middle between"><div class="padding-right-1">In our website we only use our own technical cookies for allowing you to access and use the Freesound platform (necessary cookies). Click <a href="/help/cookies_policy/">here</a> for more information.</div><button id="cookieConsentButton" class="btn-primary">Ok</button>', false);

    document.getElementById('cookieConsentButton').addEventListener('click', () => {
        setCookie("cookieConsent", "yes", 360);
        dismissToast();
    });
}
