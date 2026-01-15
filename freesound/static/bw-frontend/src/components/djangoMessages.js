import { showToast } from './toast';

const djangoMessagesContent = document.getElementById(
  'django-messages-content'
);
if (djangoMessagesContent !== null) {
  showToast(djangoMessagesContent.innerHTML);
}
