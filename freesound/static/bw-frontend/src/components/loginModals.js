// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import { showToast } from './toast';

const recoveryAccountBtn = document.getElementById('recovery-account');

const handleRecoveryAccount = () => {
  showToast("Check your email, we've sent you a link");
};

recoveryAccountBtn.addEventListener('click', handleRecoveryAccount);

// @license-end
