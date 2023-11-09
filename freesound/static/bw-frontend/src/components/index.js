// Here we import the component .js files which have some global scope code
// The rest of the components have code that will be executed through the
// initializeStuffInContainer function in utils/initHelper.js. We separate
// logic in this way because initializeStuffInContainer can be called both
// when loading a page and also when dynamically loading sections of a page
// (for example to initialize sound players and checkboxes in a modal).
import './asyncSection';
import './cookieConsent';
import './djangoMessages';
import './geotagPicker';
import './loginModals';
import './navbar';
import './player';
import './scrollSpy';
import './toast';
import './uiThemeDetector';

import { initializeStuffInContainer } from '../utils/initHelper';
initializeStuffInContainer(document, true, true, true);
