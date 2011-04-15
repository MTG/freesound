/*
   SoundManager 2: Javascript Sound for the Web
   --------------------------------------------
   http://schillmania.com/projects/soundmanager2/

   Copyright (c) 2008, Scott Schiller. All rights reserved.
   Code licensed under the BSD License:
   http://schillmania.com/projects/soundmanager2/license.txt

   V2.75a.20080707
*/

function SoundManager(smURL,smID) {
 
  this.flashVersion = 8;           // Version of flash to require, either 8 or 9. Some API features require Flash 9.
  this.debugMode = true;           // enable debugging output (div#soundmanager-debug, OR console if available + configured)
  this.useConsole = true;          // use firebug/safari console.log()-type debug console if available
  this.consoleOnly = false;        // if console is being used, do not create/write to #soundmanager-debug
  this.waitForWindowLoad = false;  // force SM2 to wait for window.onload() before trying to call soundManager.onload()
  this.nullURL = 'data/null.mp3';  // path to "null" (empty) MP3 file, used to unload sounds (Flash 8 only)
  this.defaultOptions = {
    'autoLoad': false,             // enable automatic loading (otherwise .load() will be called on demand with .play(), the latter being nicer on bandwidth - if you want to .load yourself, you also can)
    'stream': true,                // allows playing before entire file has loaded (recommended)
    'autoPlay': false,             // enable playing of file as soon as possible (much faster if "stream" is true)
    'onid3': null,                 // callback function for "ID3 data is added/available"
    'onload': null,                // callback function for "load finished"
    'whileloading': null,          // callback function for "download progress update" (X of Y bytes received)
    'onplay': null,                // callback for "play" start
    'onpause': null,               // callback for "pause"
    'onresume': null,              // callback for "resume" (pause toggle)
    'whileplaying': null,          // callback during play (position update)
    'onstop': null,                // callback for "user stop"
    'onfinish': null,              // callback function for "sound finished playing"
    'onbeforefinish': null,        // callback for "before sound finished playing (at [time])"
    'onbeforefinishtime': 5000,    // offset (milliseconds) before end of sound to trigger beforefinish (eg. 1000 msec = 1 second)
    'onbeforefinishcomplete':null, // function to call when said sound finishes playing
    'onjustbeforefinish':null,     // callback for [n] msec before end of current sound
    'onjustbeforefinishtime':200,  // [n] - if not using, set to 0 (or null handler) and event will not fire.
    'multiShot': true,             // let sounds "restart" or layer on top of each other when played multiple times, rather than one-shot/one at a time
    'usePeakData': false,          // [FLASH 9+ ONLY]: enable left/right channel peak (level) data
    'useSpectrumData': false,      // [FLASH 9+ ONLY]: enable sound spectrum (frequency data) - WARNING: CPU-INTENSIVE: may set CPUs on fire.
    'position': null,              // offset (milliseconds) to seek to within loaded sound data.
    'pan': 0,                      // "pan" settings, left-to-right, -100 to 100
    'volume': 100                  // self-explanatory. 0-100, the latter being the max.
  };
  this.allowPolling = true;        // allow flash to poll for status update (required for "while playing", peak, sound spectrum functions to work.)

  var self = this; 
  this.version = null;
  this.versionNumber = 'V2.75a.20080707';
  this.movieURL = null;
  this.url = null;
  this.swfLoaded = false;
  this.enabled = false;
  this.o = null;
  this.id = (smID||'sm2movie');
  this.oMC = null;
  this.sounds = [];
  this.soundIDs = [];
  this.isIE = (navigator.userAgent.match(/MSIE/));
  this.isSafari = (navigator.userAgent.match(/safari/i));
  this.debugID = 'soundmanager-debug';
  this._debugOpen = true;
  this._didAppend = false;
  this._appendSuccess = false;
  this._didInit = false;
  this._disabled = false;
  this._windowLoaded = false;
  this._hasConsole = (typeof console != 'undefined' && typeof console.log != 'undefined');
  this._debugLevels = ['log','info','warn','error'];
  this._defaultFlashVersion = 9;
  this.features = {
    peakData: false,
    spectrumData: false
  };
  this.sandbox = {
    'type': null,
    'types': {
      'remote': 'remote (domain-based) rules',
      'localWithFile': 'local with file access (no internet access)',
      'localWithNetwork': 'local with network (internet access only, no local access)',
      'localTrusted': 'local, trusted (local + internet access)'
    },
    'description': null,
    'noRemote': null,
    'noLocal': null
  };
  this._setVersionInfo = function() {
    if (self.flashVersion != 8 && self.flashVersion != 9) {
      alert('soundManager.flashVersion must be 8 or 9. "'+self.flashVersion+'" is invalid. Reverting to '+self._defaultFlashVersion+'.');
      self.flashVersion = self._defaultFlashVersion;
    }
    self.version = self.versionNumber+(self.flashVersion==9?' (AS3/Flash 9)':' (AS2/Flash 8)');
    self.movieURL = (self.flashVersion==8?'soundmanager2.swf':'soundmanager2_flash9.swf');
    self.features.peakData = (self.flashVersion>=9);
    self.features.spectrumData = (self.flashVersion>=9);
  }
  this._overHTTP = (document.location?document.location.protocol.match(/http/i):null);
  this._waitingforEI = false;
  this._initPending = false;
  this._tryInitOnFocus = (this.isSafari && typeof document.hasFocus == 'undefined');
  this._isFocused = (typeof document.hasFocus != 'undefined'?document.hasFocus():null);
  this._okToDisable = !this._tryInitOnFocus;
  var flashCPLink = 'http://www.macromedia.com/support/documentation/en/flashplayer/help/settings_manager04.html';

  // --- public methods ---
  
  this.supported = function() {
    return (self._didInit && !self._disabled);
  };

  this.getMovie = function(smID) {
    return self.isIE?window[smID]:(self.isSafari?document.getElementById(smID+'embed')||document[smID+'embed']:document.getElementById(smID+'embed'));
  };

  this.loadFromXML = function(sXmlUrl) {
    try {
      self.o._loadFromXML(sXmlUrl);
    } catch(e) {
      self._failSafely();
      return true;
    };
  };

  this.createSound = function(oOptions) {
    if (!self._didInit) throw new Error('soundManager.createSound(): Not loaded yet - wait for soundManager.onload() before calling sound-related methods');
    if (arguments.length==2) {
      // function overloading in JS! :) ..assume simple createSound(id,url) use case
      oOptions = {'id':arguments[0],'url':arguments[1]};
    };
    var thisOptions = self._mergeObjects(oOptions); // inherit SM2 defaults
    self._writeDebug('soundManager.createSound(): '+thisOptions.id+' ('+thisOptions.url+')',1);
    if (self._idCheck(thisOptions.id,true)) {
      self._writeDebug('soundManager.createSound(): '+thisOptions.id+' exists',1);
      return self.sounds[thisOptions.id];
    };
    self.sounds[thisOptions.id] = new SMSound(self,thisOptions);
    self.soundIDs[self.soundIDs.length] = thisOptions.id;
    try {
      // AS2:
      if (self.flashVersion==8) {
        self.o._createSound(thisOptions.id,thisOptions.onjustbeforefinishtime);
      } else {
        self.o._createSound(thisOptions.id,thisOptions.url,thisOptions.onjustbeforefinishtime,thisOptions.usePeakData,thisOptions.useSpectrumData);
      }
    } catch(e) {
      self._failSafely();
      return true;
    };
    if (thisOptions.autoLoad || thisOptions.autoPlay) window.setTimeout(function(){self.sounds[thisOptions.id].load(thisOptions);},20);
    if (thisOptions.autoPlay) self.sounds[thisOptions.id].playState = 1; // we can only assume this sound will be playing soon.
    return self.sounds[thisOptions.id];
  };

  this.destroySound = function(sID) {
    // explicitly destroy a sound before normal page unload, etc.
    if (!self._idCheck(sID)) return false;
    for (var i=0; i<self.soundIDs.length; i++) {
      if (self.soundIDs[i] == sID) {
	self.soundIDs.splice(i,1);
        continue;
      };
    };
    self.sounds[sID].unload();
    delete self.sounds[sID];
  };

  this.load = function(sID,oOptions) {
    if (!self._idCheck(sID)) return false;
    self.sounds[sID].load(oOptions);
  };

  this.unload = function(sID) {
    if (!self._idCheck(sID)) return false;
    self.sounds[sID].unload();
  };

  this.play = function(sID,oOptions) {
    if (!self._idCheck(sID)) {
      if (typeof oOptions != 'Object') oOptions = {url:oOptions}; // overloading use case: play('mySound','/path/to/some.mp3');
      if (oOptions && oOptions.url) {
        // overloading use case, creation + playing of sound: .play('someID',{url:'/path/to.mp3'});
        self._writeDebug('soundController.play(): attempting to create "'+sID+'"',1);
        oOptions.id = sID;
        self.createSound(oOptions);
      } else {
        return false;
      };
    };
    self.sounds[sID].play(oOptions);
  };

  this.start = this.play; // just for convenience

  this.setPosition = function(sID,nMsecOffset) {
    if (!self._idCheck(sID)) return false;
    self.sounds[sID].setPosition(nMsecOffset);
  };

  this.stop = function(sID) {
    if (!self._idCheck(sID)) return false;
    self._writeDebug('soundManager.stop('+sID+')',1);
    self.sounds[sID].stop(); 
  };

  this.stopAll = function() {
    self._writeDebug('soundManager.stopAll()',1);
    for (var oSound in self.sounds) {
      if (self.sounds[oSound] instanceof SMSound) self.sounds[oSound].stop(); // apply only to sound objects
    };
  };

  this.pause = function(sID) {
    if (!self._idCheck(sID)) return false;
    self.sounds[sID].pause();
  };

  this.resume = function(sID) {
    if (!self._idCheck(sID)) return false;
    self.sounds[sID].resume();
  };

  this.togglePause = function(sID) {
    if (!self._idCheck(sID)) return false;
    self.sounds[sID].togglePause();
  };

  this.setPan = function(sID,nPan) {
    if (!self._idCheck(sID)) return false;
    self.sounds[sID].setPan(nPan);
  };

  this.setVolume = function(sID,nVol) {
    if (!self._idCheck(sID)) return false;
    self.sounds[sID].setVolume(nVol);
  };

  this.mute = function(sID) {
    if (!sID) {
      var o = null;
      self._writeDebug('soundManager.mute(): Muting all sounds');
      for (o in self.sounds) {
        self.sounds[o].mute();
      }
    } else {
      if (!self._idCheck(sID)) return false;
      self._writeDebug('soundManager.mute(): Muting "'+sID+'"');
      self.sounds[sID].mute();
    }
  };

  this.unmute = function(sID) {
    if (!sID) {
      var o = null;
      self._writeDebug('soundManager.unmute(): Unmuting all sounds');
      for (o in self.sounds) {
        self.sounds[o].unmute();
      }
    } else {
      if (!self._idCheck(sID)) return false;
      self._writeDebug('soundManager.unmute(): Unmuting "'+sID+'"');
      self.sounds[sID].unmute();
    }
  };

  this.setPolling = function(bPolling) {
    if (!self.o || !self.allowPolling) return false;
    // self._writeDebug('soundManager.setPolling('+bPolling+')');
    self.o._setPolling(bPolling);
  };

  this.disable = function() {
    // destroy all functions
    if (self._disabled) return false;
    self._disabled = true;
    self._writeDebug('soundManager.disable(): Disabling all functions - future calls will return false.',1);
    for (var i=self.soundIDs.length; i--;) {
      self._disableObject(self.sounds[self.soundIDs[i]]);
    };
    self.initComplete(); // fire "complete", despite fail
    self._disableObject(self);
  };

  this.getSoundById = function(sID,suppressDebug) {
    if (!sID) throw new Error('SoundManager.getSoundById(): sID is null/undefined');
    var result = self.sounds[sID];
    if (!result && !suppressDebug) {
      self._writeDebug('"'+sID+'" is an invalid sound ID.',2);
      // soundManager._writeDebug('trace: '+arguments.callee.caller);
    };
    return result;
  };

  this.onload = function() {
    // window.onload() equivalent for SM2, ready to create sounds etc.
    // this is a stub - you can override this in your own external script, eg. soundManager.onload = function() {}
    soundManager._writeDebug('<em>Warning</em>: soundManager.onload() is undefined.',2);
  };

  this.onerror = function() {
    // stub for user handler, called when SM2 fails to load/init
  };

  // --- "private" methods ---

  this._idCheck = this.getSoundById;

  this._disableObject = function(o) {
    for (var oProp in o) {
      if (typeof o[oProp] == 'function' && typeof o[oProp]._protected == 'undefined') o[oProp] = function(){return false;};
    };
    oProp = null;
  };

  this._failSafely = function() {
    // exception handler for "object doesn't support this property or method" or general failure
    var fpgssTitle = 'You may need to whitelist this location/domain eg. file:///C:/ or C:/ or mysite.com, or set ALWAYS ALLOW under the Flash Player Global Security Settings page. The latter is probably less-secure.';
    var flashCPL = '<a href="'+flashCPLink+'" title="'+fpgssTitle+'">view/edit</a>';
    var FPGSS = '<a href="'+flashCPLink+'" title="Flash Player Global Security Settings">FPGSS</a>';
    if (!self._disabled) {
      self._writeDebug('soundManager: Failed to initialise.',2);
      self.disable();
    };
  };
  
  this._normalizeMovieURL = function(smURL) {
    if (smURL) {
      if (smURL.match(/\.swf/)) {
        smURL = smURL.substr(0,smURL.lastIndexOf('.swf'));
      }
      if (smURL.lastIndexOf('/') != smURL.length-1) {
        smURL = smURL+'/';
      }
    }
    return(smURL && smURL.lastIndexOf('/')!=-1?smURL.substr(0,smURL.lastIndexOf('/')+1):'./')+self.movieURL;
  }

  this._createMovie = function(smID,smURL) {
    if (self._didAppend && self._appendSuccess) return false; // ignore if already succeeded
    if (window.location.href.indexOf('debug=1')+1) self.debugMode = true; // allow force of debug mode via URL
    self._didAppend = true;
	
    // safety check for legacy (change to Flash 9 URL)
    self._setVersionInfo();
    self.url = self._normalizeMovieURL(smURL?smURL:self.url);
    smURL = self.url;

    var html = ['<object id="'+smID+'" data="'+smURL+'" type="application/x-shockwave-flash" width="1" height="1"><param name="movie" value="'+smURL+'" /><param name="AllowScriptAccess" value="always" /></object>','<object id="'+smID+'embed" data="'+smURL+'" type="application/x-shockwave-flash" width="1" height="1"><param name="movie" value="'+smURL+'" /><param name="AllowScriptAccess" value="always" /></object>'];

    var toggleElement = '<div id="'+self.debugID+'-toggle" style="position:fixed;_position:absolute;right:0px;bottom:0px;_top:0px;width:1.2em;height:1.2em;line-height:1.2em;margin:2px;padding:0px;text-align:center;border:1px solid #999;cursor:pointer;background:#fff;color:#333;z-index:706" title="Toggle SM2 debug console" onclick="soundManager._toggleDebug()">-</div>';
    var debugHTML = '<div id="'+self.debugID+'" style="display:'+(self.debugMode && ((!self._hasConsole||!self.useConsole)||(self.useConsole && self._hasConsole && !self.consoleOnly))?'block':'none')+';opacity:0.85"></div>';
    var appXHTML = 'soundManager._createMovie(): appendChild/innerHTML set failed. May be app/xhtml+xml DOM-related.';
    var sHTML = '<div style="position:absolute;left:-256px;top:-256px;width:1px;height:1px" class="movieContainer">'+html[self.isIE?0:1]+'</div>'+(self.debugMode && ((!self._hasConsole||!self.useConsole)||(self.useConsole && self._hasConsole && !self.consoleOnly)) && !document.getElementById(self.debugID)?'x'+debugHTML+toggleElement:'');

    var oTarget = (document.body?document.body:(document.documentElement?document.documentElement:document.getElementsByTagName('div')[0]));
    if (oTarget) {
      self.oMC = document.createElement('div');
      self.oMC.className = 'movieContainer';
      // "hide" flash movie
      self.oMC.style.position = 'absolute';
      self.oMC.style.left = '-256px';
      self.oMC.style.width = '1px';
      self.oMC.style.height = '1px';
      try {
        oTarget.appendChild(self.oMC);
        self.oMC.innerHTML = html[self.isIE?0:1];
        self._appendSuccess = true;
      } catch(e) {
        // may fail under app/xhtml+xml - has yet to be tested
        throw new Error(appXHTML);
      };
      if (!document.getElementById(self.debugID) && ((!self._hasConsole||!self.useConsole)||(self.useConsole && self._hasConsole && !self.consoleOnly))) {
        var oDebug = document.createElement('div');
        oDebug.id = self.debugID;
        oDebug.style.display = (self.debugMode?'block':'none');
        if (self.debugMode) {
          try {
            var oD = document.createElement('div');
            oTarget.appendChild(oD);
            oD.innerHTML = toggleElement;
          } catch(e) {
            throw new Error(appXHTML);
          };
        };
        oTarget.appendChild(oDebug);
      };
      oTarget = null;
    };
    self._writeDebug('-- SoundManager 2 '+self.version+' --',1);
    self._writeDebug('soundManager._createMovie(): Trying to load '+smURL,1);
  };

  this._writeDebug = function(sText,sType,bTimestamp) {
    if (!self.debugMode) return false;
    if (typeof bTimestamp != 'undefined' && bTimestamp) {
      sText = sText + ' | '+new Date().getTime();
    };
    if (self._hasConsole && self.useConsole) {
      var sMethod = self._debugLevels[sType];
      if (typeof console[sMethod] != 'undefined') {
        console[sMethod](sText);
      } else {
        console.log(sText);
      };
      if (self.useConsoleOnly) return true;
    };
    var sDID = 'soundmanager-debug';
    try {
      var o = document.getElementById(sDID);
      if (!o) return false;
      var oItem = document.createElement('div');
      sText = sText.replace(/\n/g,'<br />');
      if (typeof sType == 'undefined') {
        var sType = 0;
      } else {
        sType = parseInt(sType);
      };
      oItem.innerHTML = sText;
      if (sType) {
        if (sType >= 2) oItem.style.fontWeight = 'bold';
        if (sType == 3) oItem.style.color = '#ff3333';
      };
      // o.appendChild(oItem); // top-to-bottom
      o.insertBefore(oItem,o.firstChild); // bottom-to-top
    } catch(e) {
      // oh well
    };
    o = null;
  };
  this._writeDebug._protected = true;

  this._writeDebugAlert = function(sText) { alert(sText); };

  if (window.location.href.indexOf('debug=alert')+1 && self.debugMode) {
    self._writeDebug = self._writeDebugAlert;
  };

  this._toggleDebug = function() {
    var o = document.getElementById(self.debugID);
    var oT = document.getElementById(self.debugID+'-toggle');
    if (!o) return false;
    if (self._debugOpen) {
      // minimize
      oT.innerHTML = '+';
      o.style.display = 'none';
    } else {
      oT.innerHTML = '-';
      o.style.display = 'block';
    };
    self._debugOpen = !self._debugOpen;
  };

  this._toggleDebug._protected = true;

  this._debug = function() {
    self._writeDebug('soundManager._debug(): sounds by id/url:',0);
    for (var i=0,j=self.soundIDs.length; i<j; i++) {
      self._writeDebug(self.sounds[self.soundIDs[i]].sID+' | '+self.sounds[self.soundIDs[i]].url,0);
    };
  };

  this._mergeObjects = function(oMain,oAdd) {
    // non-destructive merge
    var o1 = {}; // clone o1
    for (var i in oMain) {
      o1[i] = oMain[i];
    }
    var o2 = (typeof oAdd == 'undefined'?self.defaultOptions:oAdd);
    for (var o in o2) {
      if (typeof o1[o] == 'undefined') o1[o] = o2[o];
    };
    return o1;
  };

  this.createMovie = function(sURL) {
    if (sURL) self.url = sURL;
    self._initMovie();
  };

  this.go = this.createMovie; // nice alias

  this._initMovie = function() {
    // attempt to get, or create, movie
    if (self.o) return false; // pre-init may have fired this function before window.onload(), may already exist
    self.o = self.getMovie(self.id); // try to get flash movie (inline markup)
    if (!self.o) {
      // try to create
      self._createMovie(self.id,self.url);
      self.o = self.getMovie(self.id);
    };
    if (self.o) {
      self._writeDebug('soundManager._initMovie(): Got '+self.o.nodeName+' element ('+(self._didAppend?'created via JS':'static HTML')+')',1);
      self._writeDebug('soundManager._initMovie(): Waiting for ExternalInterface call from Flash..');
    };
  };

  this.waitForExternalInterface = function() {
    if (self._waitingForEI) return false;
    self._waitingForEI = true;
    if (self._tryInitOnFocus && !self._isFocused) {
      self._writeDebug('soundManager: Special case: Flash may not have started due to non-focused tab (Safari is lame), and/or focus cannot be detected. Waiting for focus-related event..');
      return false;
    };
    if (!self._didInit) {
      self._writeDebug('soundManager: Getting impatient, still waiting for Flash.. ;)');
    };
    setTimeout(function() {
      if (!self._didInit) {
        self._writeDebug('soundManager: No Flash response within reasonable time after document load.\nPossible causes: Flash version under 8, no support, or Flash security denying JS-Flash communication.',2);
        if (!self._overHTTP) {
          self._writeDebug('soundManager: Loading this page from local/network file system (not over HTTP?) Flash security likely restricting JS-Flash access. Consider adding current URL to "trusted locations" in the Flash player security settings manager at '+flashCPLink+', or simply serve this content over HTTP.',2);
        };
      };
      // if still not initialized and no other options, give up
      if (!self._didInit && self._okToDisable) self._failSafely();
    },750);
  };

  this.handleFocus = function() {
    if (self._isFocused || !self._tryInitOnFocus) return true;
    self._okToDisable = true;
    self._isFocused = true;
    self._writeDebug('soundManager.handleFocus()');
    if (self._tryInitOnFocus) {
      // giant Safari 3.1 hack - assume window in focus if mouse is moving, since document.hasFocus() not currently implemented.
      window.removeEventListener('mousemove',self.handleFocus,false);
    };
    // allow init to restart
    self._waitingForEI = false;
    setTimeout(self.waitForExternalInterface,500);
    // detach event
    if (window.removeEventListener) {
      window.removeEventListener('focus',self.handleFocus,false);
    } else if (window.detachEvent) {
      window.detachEvent('onfocus',self.handleFocus);
    };
  };

  this.initComplete = function() {
    if (self._didInit) return false;
    self._didInit = true;
    self._writeDebug('-- SoundManager 2 '+(self._disabled?'failed to load':'loaded')+' ('+(self._disabled?'security/load error':'OK')+') --',1);
    if (self._disabled) {
      self._writeDebug('soundManager.initComplete(): calling soundManager.onerror()',1);
      self.onerror.apply(window);
      return false;
    };
    if (self.waitForWindowLoad && !self._windowLoaded) {
      self._writeDebug('soundManager: Waiting for window.onload()');
      if (window.addEventListener) {
        window.addEventListener('load',self.initUserOnload,false);
      } else if (window.attachEvent) {
        window.attachEvent('onload',self.initUserOnload);
      };
      return false;
    } else {
      if (self.waitForWindowLoad && self._windowLoaded) {
        self._writeDebug('soundManager: Document already loaded');
      };
      self.initUserOnload();
    };
  };

  this.initUserOnload = function() {
    self._writeDebug('soundManager.initComplete(): calling soundManager.onload()',1);
    // call user-defined "onload", scoped to window
    try {
      self.onload.apply(window);
    } catch(e) {
      // something broke (likely JS error in user function)
      self._writeDebug('soundManager.onload() threw an exception: '+e.message,2);
      setTimeout(function(){throw new Error(e)},20);
      return false;
    };
    self._writeDebug('soundManager.onload() complete',1);
  };

  this.init = function() {
    self._writeDebug('-- soundManager.init() --');
    // called after onload()
    self._initMovie();
    if (self._didInit) {
      self._writeDebug('soundManager.init(): Already called?');
      return false;
    };
    // event cleanup
    if (window.removeEventListener) {
      window.removeEventListener('load',self.beginDelayedInit,false);
    } else if (window.detachEvent) {
      window.detachEvent('onload',self.beginDelayedInit);
    };
    try {
      self._writeDebug('Attempting to call JS-Flash..');
      self.o._externalInterfaceTest(false); // attempt to talk to Flash
      // self._writeDebug('Flash ExternalInterface call (JS-Flash) OK',1);
      if (!self.allowPolling) self._writeDebug('Polling (whileloading/whileplaying support) is disabled.',1);
      self.setPolling(true);
	  if (!self.debugMode) self.o._disableDebug();
      self.enabled = true;
    } catch(e) {
      self._failSafely();
      self.initComplete();
      return false;
    };
    self.initComplete();
  };

  this.beginDelayedInit = function() {
    self._writeDebug('soundManager.beginDelayedInit(): Document loaded');
    self._windowLoaded = true;
    setTimeout(self.waitForExternalInterface,500);
    setTimeout(self.beginInit,20);
  };

  this.beginInit = function() {
    if (self._initPending) return false;
    self.createMovie(); // ensure creation if not already done
    self._initMovie();
    self._initPending = true;
    return true;
  };

  this.domContentLoaded = function() {
    self._writeDebug('soundManager.domContentLoaded()');
    if (document.removeEventListener) document.removeEventListener('DOMContentLoaded',self.domContentLoaded,false);
    self.go();
  };

  this._externalInterfaceOK = function() {
    // callback from flash for confirming that movie loaded, EI is working etc.
    if (self.swfLoaded) return false;
    self._writeDebug('soundManager._externalInterfaceOK()');
    self.swfLoaded = true;
    self._tryInitOnFocus = false;
    if (self.isIE) {
      // IE needs a timeout OR delay until window.onload - may need TODO: investigating
      setTimeout(self.init,100);
    } else {
      self.init();
    };
  };

  this._setSandboxType = function(sandboxType) {
    var sb = self.sandbox;
    sb.type = sandboxType;
    sb.description = sb.types[(typeof sb.types[sandboxType] != 'undefined'?sandboxType:'unknown')];
    self._writeDebug('Flash security sandbox type: '+sb.type);
    if (sb.type == 'localWithFile') {
      sb.noRemote = true;
      sb.noLocal = false;
      self._writeDebug('Flash security note: Network/internet URLs will not load due to security restrictions. Access can be configured via Flash Player Global Security Settings Page: http://www.macromedia.com/support/documentation/en/flashplayer/help/settings_manager04.html',2);
    } else if (sb.type == 'localWithNetwork') {
      sb.noRemote = false;
      sb.noLocal = true;
    } else if (sb.type == 'localTrusted') {
      sb.noRemote = false;
      sb.noLocal = false;
    };
  };

  this.destruct = function() {
    self._writeDebug('soundManager.destruct()');
    self.disable();
  };
  
  // SMSound (sound object)
  
  function SMSound(oSM,oOptions) {
  var self = this;
  var sm = oSM;
  this.sID = oOptions.id;
  this.url = oOptions.url;
  this.options = sm._mergeObjects(oOptions);
  this.instanceOptions = this.options; // per-play-instance-specific options

  this._debug = function() {
    if (sm.debugMode) {
    var stuff = null;
    var msg = [];
    var sF = null;
    var sfBracket = null;
    var maxLength = 64; // # of characters of function code to show before truncating
    for (stuff in self.options) {
      if (self.options[stuff] != null) {
        if (self.options[stuff] instanceof Function) {
	  // handle functions specially
	  sF = self.options[stuff].toString();
	  sF = sF.replace(/\s\s+/g,' '); // normalize spaces
	  sfBracket = sF.indexOf('{');
	  msg[msg.length] = ' '+stuff+': {'+sF.substr(sfBracket+1,(Math.min(Math.max(sF.indexOf('\n')-1,maxLength),maxLength))).replace(/\n/g,'')+'... }';
	} else {
	  msg[msg.length] = ' '+stuff+': '+self.options[stuff];
	};
      };
    };
    sm._writeDebug('SMSound() merged options: {\n'+msg.join(', \n')+'\n}');
    };
  };

  this._debug();

  this.id3 = {
   /* 
    Name/value pairs set via Flash when available - see reference for names:
    http://livedocs.macromedia.com/flash/8/main/wwhelp/wwhimpl/common/html/wwhelp.htm?context=LiveDocs_Parts&file=00001567.html
    (eg., this.id3.songname or this.id3['songname'])
   */
  };

  self.resetProperties = function(bLoaded) {
    self.bytesLoaded = null;
    self.bytesTotal = null;
    self.position = null;
    self.duration = null;
    self.durationEstimate = null;
    self.loaded = false;
    self.loadSuccess = null;
    self.playState = 0;
    self.paused = false;
    self.readyState = 0; // 0 = uninitialised, 1 = loading, 2 = failed/error, 3 = loaded/success
    self.didBeforeFinish = false;
    self.didJustBeforeFinish = false;
    self.instanceOptions = {};
    self.instanceCount = 0;
    self.peakData = {
      left: 0,
      right: 0
    };
    self.spectrumData = [];
  };

  self.resetProperties();

  // --- public methods ---

  this.load = function(oOptions) {
    self.loaded = false;
    self.loadSuccess = null;
    self.readyState = 1;
    self.playState = (oOptions.autoPlay?1:0); // if autoPlay, assume "playing" is true (no way to detect when it actually starts in Flash unless onPlay is watched?)
    self.instanceOptions = sm._mergeObjects(oOptions);
    if (typeof self.instanceOptions.url == 'undefined') self.instanceOptions.url = self.url;
    try {
      sm._writeDebug('soundManager.load(): '+self.instanceOptions.url,1);
	  if (sm.flashVersion==8) {
	    sm.o._load(self.sID,self.instanceOptions.url,self.instanceOptions.stream,self.instanceOptions.autoPlay,(self.instanceOptions.whileloading?1:0));
	  } else {
        sm.o._load(self.sID,self.instanceOptions.url,self.instanceOptions.stream?true:false,self.instanceOptions.autoPlay?true:false); // ,(thisOptions.whileloading?true:false)
	  }
    } catch(e) {
      sm._writeDebug('SMSound().load(): JS-Flash communication failed.',2);
    };
  };

  this.unload = function() {
    // Flash 8/AS2 can't "close" a stream - fake it by loading an empty MP3
    // Flash 9/AS3: Close stream, preventing further load
    sm._writeDebug('SMSound().unload(): "'+self.sID+'"');
    self.setPosition(0); // reset current sound positioning
    sm.o._unload(self.sID,sm.nullURL);
    // reset load/status flags
    self.resetProperties();
  };

  this.play = function(oOptions) {
    if (!oOptions) oOptions = {};
    self.instanceOptions = sm._mergeObjects(oOptions,self.instanceOptions);
    self.instanceOptions = sm._mergeObjects(self.instanceOptions,self.options);
    if (self.playState == 1) {
      var allowMulti = self.instanceOptions.multiShot;
      if (!allowMulti) {
        sm._writeDebug('SMSound.play(): "'+self.sID+'" already playing (one-shot)',1);
        return false;
      } else {
        sm._writeDebug('SMSound.play(): "'+self.sID+'" already playing (multi-shot)',1);
      };
    };
    if (!self.loaded) {
      if (self.readyState == 0) {
        sm._writeDebug('SMSound.play(): Attempting to load "'+self.sID+'"',1);
        // try to get this sound playing ASAP
        self.instanceOptions.stream = true;
        self.instanceOptions.autoPlay = true;
        // TODO: need to investigate when false, double-playing
        // if (typeof oOptions.autoPlay=='undefined') thisOptions.autoPlay = true; // only set autoPlay if unspecified here
        self.load(self.instanceOptions); // try to get this sound playing ASAP
      } else if (self.readyState == 2) {
        sm._writeDebug('SMSound.play(): Could not load "'+self.sID+'" - exiting',2);
        return false;
      } else {
        sm._writeDebug('SMSound.play(): "'+self.sID+'" is loading - attempting to play..',1);
      };
    } else {
      sm._writeDebug('SMSound.play(): "'+self.sID+'"');
    };
    if (self.paused) {
      self.resume();
    } else {
      self.playState = 1;
      if (!self.instanceCount || sm.flashVersion == 9) self.instanceCount++;
      self.position = (typeof self.instanceOptions.position != 'undefined' && !isNaN(self.instanceOptions.position)?self.instanceOptions.position:0);
      if (self.instanceOptions.onplay) self.instanceOptions.onplay.apply(self);
      self.setVolume(self.instanceOptions.volume);
      self.setPan(self.instanceOptions.pan);
      if (sm.flashVersion != 8 || (sm.flashVersion == 8 && !self.instanceOptions.autoPlay)) {
       // sm._writeDebug('starting sound '+self.sID);
       sm.o._start(self.sID,self.instanceOptions.loop||1,(sm.flashVersion==9?self.position:self.position/1000)); // TODO: verify !autoPlay doesn't cause issue
      };
    };
  };

  this.start = this.play; // just for convenience

  this.stop = function(bAll) {
    if (self.playState == 1) {
      self.playState = 0;
      self.paused = false;
      // if (sm.defaultOptions.onstop) sm.defaultOptions.onstop.apply(self);
      if (self.instanceOptions.onstop) self.instanceOptions.onstop.apply(self);
      sm.o._stop(self.sID);
      self.instanceCount = 0;
      self.instanceOptions = {};
    };
  };

  this.setPosition = function(nMsecOffset) {
    self.instanceOptions.position = nMsecOffset; // (sm.flashVersion==9?nMsecOffset:nMsecOffset); // update local options
    // if (sm.flashVersion==8) self.options.position = self.instanceOptions.position;
    sm.o._setPosition(self.sID,(sm.flashVersion==9?self.instanceOptions.position:self.instanceOptions.position/1000),(self.paused||!self.playState)); // if paused or not playing, will not resume (by playing)
  };

  this.pause = function() {
    if (self.paused) return false;
    sm._writeDebug('SMSound.pause()');
    self.paused = true;
    sm.o._pause(self.sID);
    if (self.instanceOptions.onpause) self.instanceOptions.onpause.apply(self);
  };

  this.resume = function() {
    if (!self.paused) return false;
    sm._writeDebug('SMSound.resume()');
    self.paused = false;
    sm.o._pause(self.sID); // flash method is toggle-based (pause/resume)
    if (self.instanceOptions.onresume) self.instanceOptions.onresume.apply(self);
  };

  this.togglePause = function() {
    sm._writeDebug('SMSound.togglePause()');
    if (!self.playState) {
      self.play({position:(sm.flashVersion==9?self.position:self.position/1000)});
      return false;
    };
    if (self.paused) {
      self.resume();
    } else {
      self.pause();
    };
  };

  this.setPan = function(nPan) {
    if (typeof nPan == 'undefined') nPan = 0;
    sm.o._setPan(self.sID,nPan);
    self.instanceOptions.pan = nPan;
  };

  this.setVolume = function(nVol) {
    if (typeof nVol == 'undefined') nVol = 100;
    sm.o._setVolume(self.sID,nVol);
    self.instanceOptions.volume = nVol;
  };

  this.mute = function() {
    sm.o._setVolume(self.sID,0);
  };

  this.unmute = function() {
    sm.o._setVolume(self.sID,self.instanceOptions.volume);
  };

  // --- "private" methods called by Flash ---

  this._whileloading = function(nBytesLoaded,nBytesTotal,nDuration) {
    self.bytesLoaded = nBytesLoaded;
    self.bytesTotal = nBytesTotal;
    self.duration = Math.floor(nDuration);
    self.durationEstimate = parseInt((self.bytesTotal/self.bytesLoaded)*self.duration); // estimate total time (will only be accurate with CBR MP3s.)
    if (self.readyState != 3 && self.instanceOptions.whileloading) self.instanceOptions.whileloading.apply(self);
    // soundManager._writeDebug('duration/durationEst: '+self.duration+' / '+self.durationEstimate);
  };

  this._onid3 = function(oID3PropNames,oID3Data) {
    // oID3PropNames: string array (names)
    // ID3Data: string array (data)
    sm._writeDebug('SMSound()._onid3(): "'+this.sID+'" ID3 data received.');
    var oData = [];
    for (var i=0,j=oID3PropNames.length; i<j; i++) {
      oData[oID3PropNames[i]] = oID3Data[i];
      // sm._writeDebug(oID3PropNames[i]+': '+oID3Data[i]);
    };
    self.id3 = sm._mergeObjects(self.id3,oData);
    if (self.instanceOptions.onid3) self.instanceOptions.onid3.apply(self);
  };

  this._whileplaying = function(nPosition,oPeakData,oSpectrumData) {
    if (isNaN(nPosition) || nPosition == null) return false; // Flash may return NaN at times
    self.position = nPosition;
	if (self.instanceOptions.usePeakData && typeof oPeakData != 'undefined' && oPeakData) {
	  self.peakData = {
	   left: oPeakData.leftPeak,
	   right: oPeakData.rightPeak
	  }
	  // sm._writeDebug('peakData '+oPeakData+': '+self.peakData.left+', '+self.peakData.right);
	}
	if (self.instanceOptions.useSpectrumData && typeof oSpectrumData != 'undefined' && oSpectrumData) {
	  // sm._writeDebug('spectrumData: '+oSpectrumData);
	  // sm._writeDebug('spectrumData length: '+oSpectrumData.length);
	  self.spectrumData = oSpectrumData;
	  /*
	  self.spectrumData = {
	   left: oSpectrumData.left.split(','),
	   right: oSpectrumData.right.split(',')
	  }
	  */
	}
    if (self.playState == 1) {
      if (self.instanceOptions.whileplaying) self.instanceOptions.whileplaying.apply(self); // flash may call after actual finish
      if (self.loaded && self.instanceOptions.onbeforefinish && self.instanceOptions.onbeforefinishtime && !self.didBeforeFinish && self.duration-self.position <= self.instanceOptions.onbeforefinishtime) {
        sm._writeDebug('duration-position &lt;= onbeforefinishtime: '+self.duration+' - '+self.position+' &lt= '+self.instanceOptions.onbeforefinishtime+' ('+(self.duration-self.position)+')');
        self._onbeforefinish();
      };
    };
  };

  this._onload = function(bSuccess) {
    bSuccess = (bSuccess==1?true:false);
    sm._writeDebug('SMSound._onload(): "'+self.sID+'"'+(bSuccess?' loaded.':' failed to load? - '+self.url));
    if (!bSuccess) {
      if (sm.sandbox.noRemote == true) {
        sm._writeDebug('SMSound._onload(): Reminder: Flash security is denying network/internet access',1);
      };
      if (sm.sandbox.noLocal == true) {
        sm._writeDebug('SMSound._onload(): Reminder: Flash security is denying local access',1);
      };
    };
    self.loaded = bSuccess;
    self.loadSuccess = bSuccess;
    self.readyState = bSuccess?3:2;
    if (self.instanceOptions.onload) {
      self.instanceOptions.onload.apply(self);
    };
  };

  this._onbeforefinish = function() {
    if (!self.didBeforeFinish) {
      self.didBeforeFinish = true;
      if (self.instanceOptions.onbeforefinish) self.instanceOptions.onbeforefinish.apply(self);
    };
  };

  this._onjustbeforefinish = function(msOffset) {
    // msOffset: "end of sound" delay actual value (eg. 200 msec, value at event fire time was 187)
    if (!self.didJustBeforeFinish) {
      self.didJustBeforeFinish = true;
      // soundManager._writeDebug('SMSound._onjustbeforefinish()');
      if (self.instanceOptions.onjustbeforefinish) self.instanceOptions.onjustbeforefinish.apply(self);;
    };
  };

  this._onfinish = function() {
    // sound has finished playing
    sm._writeDebug('SMSound._onfinish(): "'+self.sID+'"');
    self.playState = 0;
    self.paused = false;
    if (self.instanceOptions.onfinish) self.instanceOptions.onfinish.apply(self);
    if (self.instanceOptions.onbeforefinishcomplete) self.instanceOptions.onbeforefinishcomplete.apply(self);
    // reset some state items
    // self.setPosition(0);
    self.didBeforeFinish = false;
    self.didJustBeforeFinish = false;
    if (self.instanceCount) {
      self.instanceCount--;
      if (!self.instanceCount) {
        // reset instance options
        self.instanceCount = 0;
        self.instanceOptions = {};
      }
    }
  };

  }; // SMSound()

  // register a few event handlers
  if (window.addEventListener) {
    window.addEventListener('focus',self.handleFocus,false);
    window.addEventListener('load',self.beginDelayedInit,false);
    window.addEventListener('beforeunload',self.destruct,false);
    if (self._tryInitOnFocus) window.addEventListener('mousemove',self.handleFocus,false); // massive Safari focus hack
  } else if (window.attachEvent) {
    window.attachEvent('onfocus',self.handleFocus);
    window.attachEvent('onload',self.beginDelayedInit);
    window.attachEvent('beforeunload',self.destruct);
  } else {
    // no add/attachevent support - safe to assume no JS -> Flash either.
    soundManager.onerror();
    soundManager.disable();
  };

  if (document.addEventListener) document.addEventListener('DOMContentLoaded',self.domContentLoaded,false);

  var SM2_COPYRIGHT = [
    ' SoundManager 2: Javascript Sound for the Web ',
    ' http://schillmania.com/projects/soundmanager2/ ',
    ' Copyright (c) 2008, Scott Schiller. All rights reserved. ',
    ' Code provided under the BSD License: http://schillmania.com/projects/soundmanager2/license.txt ',
  ];

}; // SoundManager()

var soundManager = new SoundManager();
