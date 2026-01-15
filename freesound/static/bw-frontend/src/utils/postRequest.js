import { getCookie } from './cookies';

const makePostRequest = (url, data, successCallback, errorCallback) => {
  const csrftoken = getCookie('csrftoken');
  const req = new XMLHttpRequest();
  req.open('POST', url, true);
  req.onload = () => {
    if (req.status >= 200 && req.status < 300) {
      successCallback(req.responseText);
    } else {
      errorCallback(req.responseText);
    }
  };
  req.onerror = () => {
    errorCallback(req.responseText);
  };
  req.setRequestHeader('X-CSRFToken', csrftoken);
  req.setRequestHeader('X-Requested-With', 'XMLHttpRequest'); // Header needed for Django .is_ajax() to return true
  const formData = new FormData();
  for (const key in data) {
    formData.append(key, data[key]);
  }
  req.send(formData);
};

const getJSONFromPostRequestWithFetch = async (url, data) => {
  const formData = new FormData();
  for (const key in data) {
    formData.append(key, data[key]);
  }
  let response = await fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCookie('csrftoken'),
      'X-Requested-With': 'XMLHttpRequest', // Header needed for Django .is_ajax() to return true
    },
    body: formData,
  });
  const returnedData = await response.json();
  return returnedData;
};

export { makePostRequest, getJSONFromPostRequestWithFetch };
