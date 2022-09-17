// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import { getCookie, setCookie } from "../utils/cookies";
import { showToastNoTimeout, dismissToast } from "./toast";

const cookieConsentValue = getCookie("cookieConsent");
if (cookieConsentValue !== "yes") {
    showToastNoTimeout('<div class="middle between"><div class="padding-right-1">In our website we only use our own technical cookies for allowing you to access and use the Freesound platform (necessary cookies). Click <a href="/help/cookies_policy/">here</a> for more information.</div><button id="cookieConsentButton" class="btn-primary">Ok</button>');

    document.getElementById('cookieConsentButton').addEventListener('click', () => {
        setCookie("cookieConsent", "yes", 360);
        dismissToast();
    });
}

// @license-end
