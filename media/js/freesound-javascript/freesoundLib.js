/**
 * 
 * @fileoverview <br>The fressoundLib library is a javascript library for Freesound.</br> 
 */


/**
 * @author frederic font, strongly based on canoris-javascript by ciskavriezenga (http://github.com/canoris/canoris-javascript)
 */

/**
 * @class FS is the namespace of the freesound-javascript library 
 */
var FS = new function()
{
		
	this._URI_SOUND = '/sounds/<sound_id>/';
	this._URI_SOUND_ANALYSIS = '/sounds/<sound_id>/analysis/<filter>/';
	this._URI_SOUND_ANALYSIS_NO_FILTER = '/sounds/<sound_id>/analysis/<filter>';
	this._URI_SIMILAR_SOUNDS = '/sounds/<sound_id>/similar/';
	this._URI_SEARCH = '/sounds/search/';
	this._URI_USER = '/people/<user_name>/';
	this._URI_USER_SOUNDS = '/people/<user_name>/sounds/';
	this._URI_USER_PACKS = '/people/<user_name>/packs/';
	this._URI_PACK = '/packs/<pack_id>/';
	this._URI_PACK_SOUNDS = '/packs/<pack_id>/sounds/';
	
 	/**
 	 * Method to create uri for request. 
 	 * @param {string} uri Contains the standerd string for request. 
 	 * @param {array} args Contains the arguments that needs to be placed in standard string.
 	 * @returns {string} uri Contains the total uri for the request.
 	 */
	this._uri = function(uri, args){
		for (a in args) {
			uri = uri.replace(/<[\w_]+>/, args[a]);
		};
		uri = FS.FreesoundData.getBaseUri() + uri;
		return uri;
	};
	
	/**
	 * Method to split reference uri in uri and paramters
	 * @param {string} uri Contains the uri to split in uri and parameters 
	 */
	this._splitUri = function(uri)
	{
		//test uri for ? -> contains parameters
		if(/\?/.test(uri)){
			//split up uri
			var splittedUri = uri.split(/\?/);
			//save baseUri
			var baseUri = splittedUri[0];
			//save parameters
			var parameters = splittedUri[1];
			//test params for & -> contains more then one parameter
			if(/\&/.test(parameters)){	
				//split parameters
				var params =  parameters.split(/\&/); 
			}
			//else safe single parameter in array to be able to create parameter object
			else{var params = [parameters]; };
			//create object to place parameters in
			var parametersObject = {}; 
			//split up parameters strings and place in object
			for( a in params)
			{	
				var param = params[a].split(/\=/);
				eval("parametersObject."+ param[0] + "=\"" + param[1] + "\"");
			}
			//return array with baseUri and paramtersObject
			return [baseUri, parametersObject];
		} else{
			return [uri, false];	
		}
	}
}


/*======================================================================*/
/*============================= FreesoundData ============================*/
/*======================================================================*/

/**
 * @class FreesoundData class contains the API key that is necesarry for requests.
 * Without API key, RequestCreator request method won't run.
 * FreesoundData class contains the base uri of Freesound 
 * Static variables and methods.
 * @constructor
 */
FS.FreesoundData = function(){};
FS.FreesoundData.apiKey = false;
FS.FreesoundData.baseUri = 'http://tabasco.upf.edu/api'; //'http://localhost:8000/api';//

/**
 * Set Api key method, checks if handed api_key exists and saves this to FreesoundData.api_key
 * @static
 * @param {string} aKey Contains the api key that is going to be used.
 */
FS.FreesoundData.setApiKey = function(aKey){
	FS.FreesoundData.apiKey = aKey;	
};

/**
 * get api key method
 * @static
 * @returns {string} apiKey Contains the used api key.
 */
FS.FreesoundData.getApiKey = function(){
	if(FS.FreesoundData.apiKey){ return FS.FreesoundData.apiKey; }
	else {throw ("Api key is not loaded.")}; 
};

/**
 * Set base uri method, checks if handed base_uri exists and saves this to FreesoundData.prototype.base_uri
 * @static
 * @param {string} bUri Contains the base uri that is going to be used.
 */
FS.FreesoundData.setBaseUri = function(bUri){
	FS.FreesoundData.baseUri = bUri;
};

/**
 * get base uri method
 * @static
 * @returns {string} baseUri Contains the base uri that is used.
 */
FS.FreesoundData.getBaseUri = function(){
	return FS.FreesoundData.baseUri;
};


/*======================================================================*/
/*=========================== RequestCreator ===========================*/
/*======================================================================*/
/**
 * @class RequestCreator is a class with a static method to create a ajax jsonp request
 * @constructor 
 */
FS.RequestCreator = function(fsObject){
};

//timeout variable, is used for jsonp requests, when request didn't succeeded in timeout time -> request Error
FS.RequestCreator.timeout = 45000;
//boolean to set use of json or jsonp
FS.RequestCreator.useJson = false;

/**
 * Set timeout method.
 * @static
 * @param {Number} tOut Used for jsonp requests timeout time.
 */
FS.RequestCreator.setTimeout = function(tOut){
	if(!isNaN(tOut)){ FS.RequestCreator.timeout = tOut; };
}

/**
 * Set use of useJson to true or false
 * @static
 * @param {boolean} json
*/
FS.RequestCreator.setUseJson = function(json){
	if(json == true){ 
		FS.RequestCreator.useJson = true;
	}else{
		FS.RequestCreator.useJson = false;
	};
}

/**
 * Standard error function, used whith json request when no error callback method is passed.
 * @static
 * @param {object} XMLHttpRequest
 * @param {string} textStatus Describes the type of error that occurred.
 * @param {object} errorThrown Optional exception object.
 */
FS.RequestCreator.standardErrorMethod = function(XMLHttpRequest, textStatus, errorThrown){	
	var errorProps = eval('(' + XMLHttpRequest.responseText + ')');
	throw new Error("RequestCreator error, request didn't succeed. " + errorProps['explanation']);
};

/**
 * Create a request to server. 
 * @static
 * @param {string} uri Holds the uri for the request.
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {fucntion} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 * @param {array} params Contains the parameters as String that need to be send with the request.
 */
FS.RequestCreator.createGetReq = function(uri, succesCallback, errorCallback, params){	
	//get api key, needed to create a request	
	var aKey = FS.FreesoundData.getApiKey();
	//create parameter object, with api key and passed paramameters
	var dataParams = {api_key: aKey};
	//if params are passed, extend dataParams with params
	if (params) { $.extend(dataParams, params); };
	//check if errorCallback is a function, 
	//if not -> use standard error method, else combine standard errorCallback with passed errorcallback
		
	if(!$.isFunction(errorCallback)){	
		var newErrorCallback = FS.RequestCreator.standardErrorMethod;
	} else {
		var newErrorCallback = function(XMLHttpRequest, textStatus, errorThrown){
			//FS.RequestCreator.standardErrorMethod(XMLHttpRequest, textStatus, errorThrown);
			var errorProps = eval('(' + XMLHttpRequest.responseText + ')');
			errorCallback(errorProps['status_code'], errorProps['type'], errorProps['explanation']);
		};
	}; 
	
	//check with wich type of json the request needs to be made
	if(FS.RequestCreator.useJson == true){
		//send a json XMLHttpRequest 
		$.ajax({
			url: uri,
			dataType: 'json',
			data: dataParams,
			success: succesCallback,
			error: newErrorCallback,
			type: 'GET'
		});
		
	} else{
		
		$.ajax({
			url: uri,
			dataType: 'jsonp',
			data: dataParams,
			success: succesCallback,
			//error: newErrorCallback,
			type: 'GET'
		});
	}
}	


/*======================================================================*/
/*============================ FreesoundObject ===========================*/
/*======================================================================*/
/**
 * @class FreesoundObject class is used to create a base object for Sound, SoundCollection, User, Pack, etc.
 * @constructor 
 * @param {object} inProperties Contains the properties of the FreesoundObject
 */
FS.FreesoundObject = function(inProperties){
	this.object = this;
	this.loaded = true;
	
	//save properties in properties variable
	if (inProperties) { this.properties = inProperties;	}
	else {throw new Error("No properties passed to constructor of FreesoundObject.")};
};

/**
 * Get item of FreesoundObject
 * @param {string} item Contains the item name.
 * @returns {object/string} item 
 */
FS.FreesoundObject.prototype.getItem = function(item){
	//check if FreesoundObject object properties are loaded
	if(this.loaded){
		var myString =  "this.properties." + item;
		//check if propertie asked for exists
		if (eval(myString)) {
			return eval(myString);
		}
		//propertie doesn't exist, throw error
		else{throw new SyntaxError( item + " does not exist in " + this)}
	}
	//properties aren't loaded, throw error
	else {throw new Error("Properties of " + this + " are not loaded.")};
}

/**
 * Get key of FreesoundObject
 * @returns {string} key of FreesoundObject
 */
FS.FreesoundObject.prototype.key = function(){
	return this.properties.key;
}

/**
 * Reload the FreesoundObject.
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {fucntion} errorCallback Will be called when the request fails (no XMLHttpRequest passed and specified error with use of jsonp).
 */
FS.FreesoundObject.prototype.update = function(succesCallback, errorCallback){
	if(this.properties.ref)
	{
		//split uri into uri and parameters object
		var uriAndParams = FS._splitUri(this.properties.ref);
		//save this (sound, collection, pager, that is calling the update method) inside var object	
		var object = this;
		//create clossure around object, with which properties can be set 
		//and return object, to be able to pass it to callback method		
		var setProps = new function(props){
		return function(props){ object.properties = props; return object} }
		
		//call createGetReq method, use above setProps method in callback method to be able to save properties
		FS.RequestCreator.createGetReq(uriAndParams[0], function(inProperties){
			var obj = setProps(inProperties);
			if($.isFunction(succesCallback)){succesCallback(obj); };
		}, errorCallback, uriAndParams[1]);	
		this.properties = false; 	
	}else{ throw new Error("properties of object does not exist, unable to update because no ref. is present");};
}


/*======================================================================*/
/*================================ Sound ===============================*/
/*======================================================================*/
/**
 * @class Sound class, is used to get a sound. 
 * @constructor 
 * @augments FS.FreesoundObject
 */
FS.Sound = function(){this.object = this;};

/**
 * Gets corresponding sound properties and create a sound object
 * @static 
 * @param {string} sId Contains a sound id.
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */

FS.Sound.getSound = function(sId, succesCallback, errorCallback){
	
	//call createGetReq and pass it file uri, file key and callback function
	FS.RequestCreator.createGetReq(FS._uri(FS._URI_SOUND, [sId]), 
	function(inProperties)
	{
				
		//create a new File object and a new FreesoundObject 
		var newSound = new FS.Sound();
		var newFreesoundObject = new FS.FreesoundObject(inProperties);
		//use jQuery.extend to let newSound inherited from newFreesoundObject
		$.extend(newSound, newFreesoundObject);	
		
		//save newFile, by using passed clossures 
		//saveFile(newSound);
		
		//call succesCallback method	
		if($.isFunction(succesCallback)){succesCallback(newSound); };
	}, errorCallback);
}

/**
 * Get analysis of Sound object and pass these to the passed callback method 
 * @param {int} showAll Contains 0 or 1. 0 -> get recommended descriptors, if 1 -> get all descriptors
 * @param {string} filter Contains a string that contain the path to the wanted descriptor (or gorup of descriptors).
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */
FS.Sound.prototype.getAnalysis = function(showAll, filter, succesCallback, errorCallback){
	
	//if showAll is undefined -> set to 0
	if (!showAll) { showAll = 0;};
	//place showAll in object and save to params variable for request	
	var params = {all: showAll};
	
	//if filter is undefined -> set to array with one empty string
	if (!filter) { 	filter = [""];}
	
	if (filter == ""){
		var uri = FS._URI_SOUND_ANALYSIS_NO_FILTER;
	}else{
		var uri = FS._URI_SOUND_ANALYSIS;
	}
	
	//create request
	FS.RequestCreator.createGetReq(
		FS._uri(uri, [this.properties['id'], filter]), 
		function(analysis){ 
			succesCallback(analysis)
		}, errorCallback, params
	);
}

FS.Sound.prototype.getSimilarSounds = function(num_results, preset, succesCallback, errorCallback){	
	FS.SoundCollection.getSimilarSoundsFromSound(this.properties['id'], num_results, preset, succesCallback, errorCallback)
}

/*==================================================================================*/
/*================================ Sound  Collection ===============================*/
/*==================================================================================*/
/**
 * @class SoundCollection class, is used to get collections of sounds (search results, user/pack sounds...). 
 * @constructor 
 * @augments FS.FreesoundObject
 */
FS.SoundCollection = function(){this.object = this;};

/**
 * Gets the list of sounds resulting from a query
 * @static 
 * @param {string} query Contains a the search query.
 * @param {int} page Indicate the desired results page to retrieve.
 * @param {string} filter Contains filters for the query (see Freesound API documentation).
 * @param {string} sort Indicates sorting preferences for the results (see Freesound API documentation).
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */

FS.SoundCollection.getSoundsFromQuery = function(query, page, filter, sort, succesCallback, errorCallback){
	
	if (!query) { query = "";};
	
	var params = {q:query};
	if (page!=""){
		$.extend(params, {p:page} );
	}
	if (filter!=""){
		$.extend(params, {f:filter} );
	}
	if (sort!=""){
		$.extend(params, {s:sort} );
	}
	
	//call createGetReq and pass it file uri, file key and callback function
	FS.RequestCreator.createGetReq(FS._uri(FS._URI_SEARCH, [""]), 
	function(inProperties)
	{
				
		//create a new File object and a new FreesoundObject 
		var newSoundCollection = new FS.SoundCollection();
		var newFreesoundObject = new FS.FreesoundObject(inProperties);
		//use jQuery.extend to let newSound inherited from newFreesoundObject
		$.extend(newSoundCollection, newFreesoundObject);	
		
		//call succesCallback method	
		if($.isFunction(succesCallback)){succesCallback(newSoundCollection); };
	}, errorCallback, params);
}


/**
 * Gets the list of sounds uploaded by a user
 * @static 
 * @param {string} uName User name.
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */
FS.SoundCollection.getSoundsFromUser = function(uName, succesCallback, errorCallback){
	
	//call createGetReq and pass it file uri, file key and callback function
	FS.RequestCreator.createGetReq(FS._uri(FS._URI_USER_SOUNDS, [uName]), 
	function(inProperties)
	{
				
		//create a new File object and a new FreesoundObject 
		var newSoundCollection = new FS.SoundCollection();
		var newFreesoundObject = new FS.FreesoundObject(inProperties);
		//use jQuery.extend to let newSound inherited from newFreesoundObject
		$.extend(newSoundCollection, newFreesoundObject);	
		
		//call succesCallback method	
		if($.isFunction(succesCallback)){succesCallback(newSoundCollection); };
	}, errorCallback);
}


/**
 * Gets the list of sounds in a pack
 * @static 
 * @param {string} pId Pack id.
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */
FS.SoundCollection.getSoundsFromPack = function(pId, succesCallback, errorCallback){
	
	//call createGetReq and pass it file uri, file key and callback function
	FS.RequestCreator.createGetReq(FS._uri(FS._URI_PACK_SOUNDS, [pId]), 
	function(inProperties)
	{
				
		//create a new File object and a new FreesoundObject 
		var newSoundCollection = new FS.SoundCollection();
		var newFreesoundObject = new FS.FreesoundObject(inProperties);
		//use jQuery.extend to let newSound inherited from newFreesoundObject
		$.extend(newSoundCollection, newFreesoundObject);	
		
		//call succesCallback method	
		if($.isFunction(succesCallback)){succesCallback(newSoundCollection); };
	}, errorCallback);
}


/**
 * Gets the list of similar sounds to a give one
 * @static 
 * @param {string} sId target Sound id.
 * @param {int} num_results Number of results to return (not paginated).
 * @param {string} preset Preset for similarity measure (see Freesound API documentation).
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */				   

FS.SoundCollection.getSimilarSoundsFromSound = function(sId, num_results, preset, succesCallback, errorCallback){
	
	if (!num_results) { num_results = 15;};
	if (!preset) { preset = "lowlevel";};
	
	var params = {num_results: num_results,
				  preset: preset};
	
	//call createGetReq and pass it file uri, file key and callback function
	FS.RequestCreator.createGetReq(FS._uri(FS._URI_SIMILAR_SOUNDS, [sId]), 
	function(inProperties)
	{
				
		//create a new File object and a new FreesoundObject 
		var newSoundCollection = new FS.SoundCollection();
		var newFreesoundObject = new FS.FreesoundObject(inProperties);
		//use jQuery.extend to let newSound inherited from newFreesoundObject
		$.extend(newSoundCollection, newFreesoundObject);	
		
		//call succesCallback method	
		if($.isFunction(succesCallback)){succesCallback(newSoundCollection); };
	}, errorCallback, params);
}


/**
 * Gets the following page of a sound collection (search results, user sounds, pack sounds...)
 * @static 
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */

FS.SoundCollection.prototype.next =  function(succesCallback, errorCallback){

	if (this.properties['next']){
		//call createGetReq and pass it file uri, file key and callback function
		FS.RequestCreator.createGetReq(this.properties['next'], 
		function(inProperties)
		{
			
			//create a new File object and a new FreesoundObject 
			var newSoundCollection = new FS.SoundCollection();
			var newFreesoundObject = new FS.FreesoundObject(inProperties);
			//use jQuery.extend to let newSound inherited from newFreesoundObject
			$.extend(newSoundCollection, newFreesoundObject);	
			
			//call succesCallback method	
			if($.isFunction(succesCallback)){succesCallback(newSoundCollection); };
		}, errorCallback);
	}else{ throw new SyntaxError("Pager does not contain next page, not loaded or no more pages available.")};
	
}

/**
 * Gets the previous page of a sound collection (search results, user sounds, pack sounds...)
 * @static 
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */

FS.SoundCollection.prototype.previous =  function(succesCallback, errorCallback){
	
	if (this.properties['previous']){
		//call createGetReq and pass it file uri, file key and callback function
		FS.RequestCreator.createGetReq(this.properties['previous'], 
		function(inProperties)
		{
					
			//create a new File object and a new FreesoundObject 
			var newSoundCollection = new FS.SoundCollection();
			var newFreesoundObject = new FS.FreesoundObject(inProperties);
			//use jQuery.extend to let newSound inherited from newFreesoundObject
			$.extend(newSoundCollection, newFreesoundObject);	
			
			//call succesCallback method	
			if($.isFunction(succesCallback)){succesCallback(newSoundCollection); };
		}, errorCallback);
	}else{ throw new SyntaxError("Pager does not contain previous page, not loaded or already at page 0.")};
	
}

/*======================================================================*/
/*================================ User ================================*/
/*======================================================================*/
/**
 * @class User class, is used to get a user. 
 * @constructor 
 * @augments FS.FreesoundObject
 */
FS.User = function(){this.object = this;};

/**
 * Gets corresponding user properties and create a user object
 * @static 
 * @param {string} uName Contains user name.
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */

FS.User.getUser = function(uName, succesCallback, errorCallback){
	
	//call createGetReq and pass it file uri, file key and callback function
	FS.RequestCreator.createGetReq(FS._uri(FS._URI_USER, [uName]), 
	function(inProperties)
	{
				
		//create a new File object and a new FreesoundObject 
		var newUser = new FS.User();
		var newFreesoundObject = new FS.FreesoundObject(inProperties);
		//use jQuery.extend to let newSound inherited from newFreesoundObject
		$.extend(newUser, newFreesoundObject);	
		
		//call succesCallback method	
		if($.isFunction(succesCallback)){succesCallback(newUser); };
	}, errorCallback);

}

FS.User.prototype.getSounds = function(succesCallback, errorCallback){	
	FS.SoundCollection.getSoundsFromUser(this.properties['username'], succesCallback, errorCallback)
}


FS.User.prototype.getPacks = function(succesCallback, errorCallback){	
	
	var uName = this.properties['username'];
	
	//call createGetReq and pass it file uri, file key and callback function
	FS.RequestCreator.createGetReq(FS._uri(FS._URI_USER_PACKS, [uName]), 
	function(inProperties)
	{
		// Use generic FreesoundObject to handle pack list/collection
		var newFreesoundObject = new FS.FreesoundObject(inProperties);
		
		//call succesCallback method	
		if($.isFunction(succesCallback)){succesCallback(newFreesoundObject); };
		
	}, errorCallback);
	
}


/*======================================================================*/
/*================================ Pack ================================*/
/*======================================================================*/
/**
 * @class Pack class, is used to get a sound pack. 
 * @constructor 
 * @augments FS.FreesoundObject
 */
FS.Pack = function(){this.object = this;};

/**
 * Gets corresponding pack properties and create a pack object
 * @static 
 * @param {string} pId Contains pack id.
 * @param {function} succesCallback Will be called when the request succeeds.
 * @param {function} errorCallback Will be called when the request fails
 * (no XMLHttpRequest and specified error passed to errorCallback with use of jsonp)
 */

FS.Pack.getPack = function(pId, succesCallback, errorCallback){
	
	//call createGetReq and pass it file uri, file key and callback function
	FS.RequestCreator.createGetReq(FS._uri(FS._URI_PACK, [pId]), 
	function(inProperties)
	{
				
		//create a new File object and a new FreesoundObject 
		var newPack = new FS.Pack();
		var newFreesoundObject = new FS.FreesoundObject(inProperties);
		//use jQuery.extend to let newSound inherited from newFreesoundObject
		$.extend(newPack, newFreesoundObject);	
		
		//call succesCallback method	
		if($.isFunction(succesCallback)){succesCallback(newPack); };
	}, errorCallback);

}

FS.Pack.prototype.getSounds = function(succesCallback, errorCallback){
	// TODO: Pack id is not returned in the API, it has to be extracted from the info
	var pId = this.properties['ref'].split('/');
	pId = pId[pId.length - 2];
	
	FS.SoundCollection.getSoundsFromPack(pId, succesCallback, errorCallback);
}

/*======================================================================*/
/*=============================== Freesound ==============================*/
/*======================================================================*/
/**
 * @class Freesound class is the API of the Freesound Javascript Library
 * @constructor
 * @param {String} aKey Contains the api key that is going to be used.
 * @returns {Object} { sound, user, pack, soundCollection }. 
 */
Freesound = function(aKey, useJson){
	
	//check if there already exist a object of Freesound class (singleton)
	if(!Freesound.object)
	{
		if (aKey) {
			
			//set use of json
			FS.RequestCreator.setUseJson(useJson);
				
			//set api key
			FS.FreesoundData.setApiKey(aKey); 
			
			//getSound function to call FS.Sound.getSound
			var getSound = function(sId, succesCallback, errorCallback)
			{	FS.Sound.getSound(sId, succesCallback, errorCallback); };
			
			//getUser function to call FS.User.getUser
			var getUser = function(uId, succesCallback, errorCallback)
			{	FS.User.getUser(uId, succesCallback, errorCallback); };
			
			//getPack function to call FS.Pack.getPack
			var getPack = function(pId, succesCallback, errorCallback)
			{	FS.Pack.getPack(pId, succesCallback, errorCallback); };
			
			
			//functions that return sound collections
			var getSoundsFromQuery = function(query, page, filter, sort, succesCallback, errorCallback)
			{	FS.SoundCollection.getSoundsFromQuery(query, page, filter, sort, succesCallback, errorCallback); };
			
			var getSoundsFromUser = function(uName, succesCallback, errorCallback)
			{	FS.SoundCollection.getSoundsFromUser(uName, succesCallback, errorCallback); };
			
			var getSoundsFromPack = function(pId, succesCallback, errorCallback)
			{	FS.SoundCollection.getSoundsFromPack(pId, succesCallback, errorCallback); };
			
			var getSimilarSoundsFromSound = function(sId, succesCallback, errorCallback)
			{	FS.SoundCollection.getSimilarSoundsFromSound(sId, succesCallback, errorCallback); };
			
			//create Freesound object, containing public variables and methods of Freesound Library						
			var object = {
				
				getApiKey: FS.FreesoundData.getApiKey,
				getBaseUri: FS.FreesoundData.getBaseUri,
				
				getSound: getSound,
				
				getUser: getUser,
				
				getPack: getPack,
				
				getSoundsFromQuery: getSoundsFromQuery,
				getSoundsFromUser: getSoundsFromUser,
				getSoundsFromPack: getSoundsFromPack,
				getSimilarSoundsFromSound: getSimilarSoundsFromSound,
				
				setTimeout: FS.RequestCreator.setTimeout
			};
		}
		//no correct api key passed -> throw error
		else {throw "you didn't pass a api_key to constructor Freesound"; }
	}
	
	
	//return object of Freesound class
	return object;	
}