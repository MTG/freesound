package  
{
	import flash.display.Sprite;
	import flash.display.StageScaleMode;
	import flash.errors.IllegalOperationError;
	import flash.events.DataEvent;
	import flash.events.Event;
	import flash.events.HTTPStatusEvent;
	import flash.events.IOErrorEvent;
	import flash.events.MouseEvent;
	import flash.events.ProgressEvent;
	import flash.events.SecurityErrorEvent;
	import flash.external.ExternalInterface;
	import flash.net.FileFilter;
	import flash.net.FileReference;
	import flash.net.FileReferenceList;
	import flash.net.URLRequest;
	import flash.net.URLRequestMethod;
	import flash.net.URLVariables;
	import flash.utils.Dictionary;

	[SWF( backgroundColor='0xffffff', width='128', height='128', frameRate='20')]

	public class Upload extends Sprite 
	{

		[Embed(source='../media/upload.png')]
		private var _UploadBitmap : Class;
		private var _button : ClickableBitmap = new ClickableBitmap(new _UploadBitmap());
		private var _sessionId : String;
		private var _lookup : Dictionary = new Dictionary();
		private var id : int = 0;

		public function Upload()
		{
			stage.scaleMode = StageScaleMode.NO_SCALE;

			addChild(_button);
			
			if (loaderInfo.parameters["sessionid"])
			{
				_sessionId = loaderInfo.parameters["sessionid"];
				trace("got session id", _sessionId);
			}
			else
			{
				_sessionId = null;
				javascriptError(-1, "session id not present!");
			}
			
			_button.addEventListener(MouseEvent.CLICK, function (e : MouseEvent) : void 
			{
				var fileReferenceList : FileReferenceList = new FileReferenceList();
				
				fileReferenceList.addEventListener(Event.SELECT, function (e : Event):void 
				{
					for each (var file:FileReference in fileReferenceList.fileList)
					{
						uploadFile(file);
					}
				});
				
				try
				{
					fileReferenceList.browse([new FileFilter("Audio files", "*.txt"), new FileFilter("Audio files", "*.wav;*.aiff;*.aif;*.ogg;*.flac;*.mp3")]);
				}
				catch (e : IllegalOperationError)
				{
					javascriptError(-1, "illegal operation error" + e);
				}
				catch (e : ArgumentError)
				{
					javascriptError(-1, "argument error" + e);
				}
			});
		}

		private function uploadFile(file : FileReference) : void
		{
			_lookup[file] = id++;
			
			file.addEventListener(HTTPStatusEvent.HTTP_STATUS, httpStatusHandler); // Dispatched when an upload fails and an HTTP status code is available to describe the failure.
			file.addEventListener(IOErrorEvent.IO_ERROR, ioErrorHandler); // Dispatched when the upload or download fails.
			file.addEventListener(Event.OPEN, openHandler); // Dispatched when an upload or download operation starts.
			file.addEventListener(ProgressEvent.PROGRESS, progressHandler); // Dispatched periodically during the file upload or download operation.
			file.addEventListener(SecurityErrorEvent.SECURITY_ERROR, securityErrorHandler); // Dispatched when a call to the FileReference.upload() or FileReference.download() method tries to upload a file to a server or get a file from a server that is outside the caller's security sandbox.
			file.addEventListener(DataEvent.UPLOAD_COMPLETE_DATA, uploadCompleteDataHandler); // Dispatched after data is received from the server after a successful upload.
			
			var urlRequest : URLRequest = new URLRequest("/home/upload/file/");
			urlRequest.method = URLRequestMethod.POST;
			
			if (_sessionId)
			{
				var post : URLVariables = new URLVariables();
				post["sessionid"] = _sessionId;
				urlRequest.data = post;
			}
			
			file.upload(urlRequest, "file");
		}

		private function httpStatusHandler(event : HTTPStatusEvent) : void 
		{
			trace("httpStatusHandler: " + event);
		}

		private function openHandler(event : Event) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("openHandler: name=" + file.name);
			javascriptAdd(_lookup[file], file.name);
		}

		private function progressHandler(event : ProgressEvent) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("progressHandler: name=" + file.name + " bytesLoaded=" + event.bytesLoaded + " bytesTotal=" + event.bytesTotal);
			javascriptProgress(_lookup[file], 100.0 * event.bytesLoaded / event.bytesTotal);
		}

		private function uploadCompleteDataHandler(event : DataEvent) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("uploadCompleteData: " + event);
			javascriptDone(_lookup[file]);
		}

		private function ioErrorHandler(event : Event) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("ioErrorHandler: name=" + file.name);
			javascriptError(_lookup[file], "ioError");
		}

		private function securityErrorHandler(event : Event) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("securityErrorHandler: name=" + file.name + " event=" + event.toString());
			javascriptError(_lookup[file], "security error");
		}


		/**
		 * EXTERNAL INTERFACE FUNCTIONS FOLLOW
		 */
		private function javascriptError(fileId : int, message : String) : void
		{
			ExternalInterface.call("uploadError", fileId, message);
		}

		private function javascriptAdd(fileId : int, filename : String) : void
		{
			ExternalInterface.call("uploadAdd", fileId, filename);
		}

		private function javascriptProgress(fileId : int, percentage : Number) : void
		{
			ExternalInterface.call("uploadProgress", fileId, percentage);
		}

		private function javascriptDone(fileId : int) : void
		{
			ExternalInterface.call("uploadDone", fileId);
		}
	}
}
