package  
{
	import flash.net.FileReference;
	import flash.net.URLRequest;
	import flash.net.URLRequestMethod;
	import flash.net.URLVariables;

	public class UploadQueue 
	{
		private var _queue:Vector.<FileReference>;
		private var _threads : int;
		private var _url : String;
		private var _sessionId : String;
		private var _numFilesUploading : int;

		public function UploadQueue(url:String, sessionId:String, threads:int = 4):void
		{
			_queue = new Vector.<FileReference>();
			_threads = threads;
			_url = url;
			_sessionId = sessionId;
			_numFilesUploading = 0;
		}

		public function addFile(file:FileReference):void
		{
			if (_numFilesUploading < _threads)
				startUpload(file);
			else
				_queue.push(file);
		}
		
		public function removeFile(file:FileReference):void
		{
			_numFilesUploading--;
			
			if (_queue.indexOf(file) >= 0)
			{
				_queue.splice(_queue.indexOf(file), 1);
			}
			else
			{
				file.cancel();
			}

			if (_numFilesUploading < _threads && _queue.length > 0)
			{
				startUpload(_queue[0]);
				_queue.splice(0, 1);
			}
		}
		
		private function startUpload(file:FileReference):void
		{
			var urlRequest : URLRequest = new URLRequest(_url);
			urlRequest.method = URLRequestMethod.POST;
			
			var post : URLVariables = new URLVariables();
			post["sessionid"] = _sessionId;
			urlRequest.data = post;
			
			file.upload(urlRequest, "file");
			_numFilesUploading++;
		}
	}
}
