const addRecaptchaScriptTagToMainHead = element => {
  var scriptTag = element.getElementsByTagName('script')[0];
  var file = scriptTag.getAttribute('src');
  if (file.indexOf('') > -1) {
    var fileref = document.createElement('script');
    fileref.setAttribute('type', 'text/javascript');
    fileref.setAttribute('src', file);
    document.getElementsByTagName('head').item(0).appendChild(fileref);
  }
};

export { addRecaptchaScriptTagToMainHead };
