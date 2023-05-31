import {makeSoundsMapWithStaticMapFirst} from '../components/mapsMapbox';
import {handleGenericModal} from '../components/modal';
import {setURLHash, hashEquals} from '../utils/urls'
import {handleDownloadersModal} from "../components/downloadersModals";

// Latest sounds/Latest tags taps

const taps = [...document.querySelectorAll('[data-toggle="tap"]')];
const tapsElements = document.getElementsByClassName('bw-profile__tap_container');

const cleanActiveClass = () => {
  taps.forEach(tap => tap.classList.remove('active'));
  tapsElements.forEach(tapElement =>
      tapElement.classList.remove('bw-profile__tap_container__active')
  );
};

const handleTap = tap => {
  cleanActiveClass();
  const tapName = tap.dataset.target.substring(1);
  const tapContainer = document.getElementById(tapName);
  setURLHash(tapName);
  tap.classList.add('active');
  tapContainer.classList.add('bw-profile__tap_container__active');
};

taps.forEach(tap => {
  tap.addEventListener('click', () => handleTap(tap));
});

// Follow modals
const userFollowersButton = document.getElementById('user-followers-button');
const userFollowUsersButton = document.getElementById('user-following-users-button');
const userFollowTagsButton = document.getElementById('user-following-tags-button');

const removeFollowModalUrlParams = () => {
  const searchParams = new URLSearchParams(window.location.search);
  [userFollowersButton, userFollowUsersButton, userFollowTagsButton].forEach(button => {
    searchParams.delete(button.dataset.modalActivationParam);
  });
  let url = window.location.protocol + '//' + window.location.host + window.location.pathname + '?' + searchParams.toString();
  if (location.hash) {
    url += location.hash;
  }
  window.history.replaceState(null, "", url);
};

const setFollowModalUrlParamToCurrentPage = (modalActivationParam) => {
  const searchParams = new URLSearchParams(window.location.search);

  // Find current page from paginator element in loaded modal
  let page = 1;
  const genericModalWrapperElement = document.getElementById('genericModalWrapper');
  genericModalWrapperElement.getElementsByClassName('bw-pagination_selected').forEach(element => {
    page = parseInt(element.firstChild.innerHTML, 10);
  });
  searchParams.set(modalActivationParam, page);
  let url = window.location.protocol + '//' + window.location.host + window.location.pathname + '?' + searchParams.toString();
  if (location.hash) {
    url += location.hash;
  }
  window.history.replaceState(null, "", url);
};

[userFollowersButton, userFollowUsersButton, userFollowTagsButton].forEach(button => {
  button.addEventListener('click', () => {
    handleGenericModal(button.dataset.modalContentUrl, () => {
      setFollowModalUrlParamToCurrentPage(button.dataset.modalActivationParam);
    }, () => {
      removeFollowModalUrlParams();
    });
  });
});


// User geotags map
makeSoundsMapWithStaticMapFirst('latest_geotags', 'map_canvas', 'static_map_wrapper')


// Activate following modals from URL params if needbe
const urlParams = new URLSearchParams(window.location.search);
const followersModalParam = urlParams.get(userFollowersButton.dataset.modalActivationParam);
const followingModalParam = urlParams.get(userFollowUsersButton.dataset.modalActivationParam);
const followingTagsModalParam = urlParams.get(userFollowTagsButton.dataset.modalActivationParam);

if (followersModalParam) {
  handleGenericModal(userFollowersButton.dataset.modalContentUrl, () => {
    setFollowModalUrlParamToCurrentPage(userFollowersButton.dataset.modalActivationParam);
  }, () => {
    removeFollowModalUrlParams();
  });
}

if (followingModalParam) {
  handleGenericModal(userFollowUsersButton.dataset.modalContentUrl, () => {
    setFollowModalUrlParamToCurrentPage(userFollowUsersButton.dataset.modalActivationParam);
  }, () => {
    removeFollowModalUrlParams();
  });
}

if (followingTagsModalParam) {
  handleGenericModal(userFollowTagsButton.dataset.modalContentUrl, () => {
    setFollowModalUrlParamToCurrentPage(userFollowTagsButton.dataset.modalActivationParam);
  }, () => {
    removeFollowModalUrlParams();
  });
}

// Activate tap sections based on hash
taps.forEach(tap => {
  const tapName = tap.dataset.target.substring(1);
  if (hashEquals(tapName)) {
    handleTap(tap);
  }
});
