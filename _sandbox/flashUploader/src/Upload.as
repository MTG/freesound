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
	import flash.utils.Dictionary;

	[SWF( backgroundColor='0xffffff', width='128', height='128', frameRate='20')]

	public class Upload extends Sprite 
	{

		[Embed(source='../media/upload.png')]
		private var _UploadBitmap : Class;
		private var _button : ClickableBitmap = new ClickableBitmap(new _UploadBitmap());
		private var _lookup : Dictionary = new Dictionary();
		private var id : int = 0;
		private var _queue : UploadQueue;

		public function Upload()
		{
			stage.scaleMode = StageScaleMode.NO_SCALE;

			addChild(_button);
			
			
			var sessionId : String = null;
			
			if (loaderInfo.parameters["sessionid"])
			{
				sessionId = loaderInfo.parameters["sessionid"];
				trace("got session id", sessionId);
			}
			else
			{
				sessionId = null;
				javascriptError(-1, "session id not present!");
			}
			
			// http://127.0.0.1:8000
			_queue = new UploadQueue("/home/upload/file/", sessionId, loaderInfo.parameters["threads"] ? loaderInfo.parameters["threads"] : 4);
			
			_button.addEventListener(MouseEvent.CLICK, function (e : MouseEvent) : void 
			{
				var fileReferenceList : FileReferenceList = new FileReferenceList();
				
				fileReferenceList.addEventListener(Event.SELECT, function (e : Event):void 
				{
					for each (var file:FileReference in fileReferenceList.fileList)
						addFile(file);
				});
				
				try
				{
					fileReferenceList.browse([new FileFilter("Audio files", "*.wav;*.aiff;*.aif;*.ogg;*.flac;*.mp3")]);
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

		private function addFile(file : FileReference) : void 
		{
			trace("addFile", file.name);
			
			_lookup[file] = id;
			_lookup[id] = file;
			id++;
			
			file.addEventListener(HTTPStatusEvent.HTTP_STATUS, httpStatusHandler); // Dispatched when an upload fails and an HTTP status code is available to describe the failure.
			file.addEventListener(IOErrorEvent.IO_ERROR, ioErrorHandler); // Dispatched when the upload or download fails.
			file.addEventListener(Event.OPEN, openHandler); // Dispatched when an upload or download operation starts.
			file.addEventListener(ProgressEvent.PROGRESS, progressHandler); // Dispatched periodically during the file upload or download operation.
			file.addEventListener(SecurityErrorEvent.SECURITY_ERROR, securityErrorHandler); // Dispatched when a call to the FileReference.upload() or FileReference.download() method tries to upload a file to a server or get a file from a server that is outside the caller's security sandbox.
			file.addEventListener(DataEvent.UPLOAD_COMPLETE_DATA, uploadCompleteDataHandler); // Dispatched after data is received from the server after a successful upload.

			_queue.addFile(file);
			javascriptAdd(_lookup[file], file.name);
		}

		private function removeFile(file : FileReference) : void
		{
			_queue.removeFile(file);
			var fileId : int = _lookup[file];
			delete _lookup[file];
			delete _lookup[fileId];
		}

		private function httpStatusHandler(event : HTTPStatusEvent) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("httpStatusHandler", event, file.name);

			javascriptError(_lookup[file], "Http error");
			removeFile(file);
		}

		private function openHandler(event : Event) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("openHandler", event, file.name);
		}

		private function progressHandler(event : ProgressEvent) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("progressHandler", event, file.name);

			javascriptProgress(_lookup[file], 100.0 * event.bytesLoaded / event.bytesTotal);
		}

		private function uploadCompleteDataHandler(event : DataEvent) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("uploadCompleteData", event, file.name);

			javascriptDone(_lookup[file]);
			removeFile(file);
		}

		private function ioErrorHandler(event : Event) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("ioErrorHandler", event, file.name);

			javascriptError(_lookup[file], "ioError");
			removeFile(file);
		}

		private function securityErrorHandler(event : Event) : void 
		{
			var file : FileReference = FileReference(event.target);
			trace("securityErrorHandler", event, file.name);

			javascriptError(_lookup[file], "security error");
			removeFile(file);
		}

		/**
		 * EXTERNAL INTERFACE FUNCTIONS FOLLOW
		 */
		// FROM jAVASCRIPT
		public function javascriptCancel(fileId : String) : void
		{
			removeFile(FileReference(_lookup[fileId]));
		}

		// TO jAVASCRIPT
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
