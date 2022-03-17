import { getCookie, setCookie } from "../utils/cookies";
import { showToastNoTimeout, dismissToast } from "./toast";

const cookieConsentValue = getCookie("cookieConsent");
if (cookieConsentValue !== "yes") {
    showToastNoTimeout('<div class="middle between"><div class="padding-right-1">We use cookies to ensure you get the best experience on our website. By browsing our site you agree to our use of cookies. For more information check out our <a href="/help/cookies_policy/">cookies policy</a>.</div><button id="cookieConsentButton" class="btn-primary">Ok</button>');

    document.getElementById('cookieConsentButton').addEventListener('click', () => {
        setCookie("cookieConsent", "yes", 360);
        dismissToast();
    });
}
