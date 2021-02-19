import { showToast } from './toast';

const recoveryAccountBtn = document.getElementById('recovery-account');

const handleRecoveryAccount = () => {
  showToast("Check your email, we've sent you a link");
};

recoveryAccountBtn.addEventListener('click', handleRecoveryAccount);
