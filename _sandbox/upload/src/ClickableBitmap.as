package  
{
	import flash.display.Bitmap;
	import flash.display.Sprite;

	/**
	 * @author bram
	 */
	public class ClickableBitmap extends Sprite 
	{
		public function ClickableBitmap(bitmap:Bitmap)
		{
			addChild(bitmap);
		}
	}
}
