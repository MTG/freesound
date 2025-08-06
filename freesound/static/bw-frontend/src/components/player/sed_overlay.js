import { getAudioElementDurationOrDurationProperty } from './utils'

export const createDetectionOverlay = (parentNode, audioElement, detectionData, sedExperiment) => {
  console.log(sedExperiment)
  if(!detectionData){
    return;
  }

  const progressIndicatorContainer = parentNode.querySelector('.bw-player__progress-indicator-container');
  if(!progressIndicatorContainer){
    return;
  }

  const existingOverlay = progressIndicatorContainer.querySelector('.bw-player__detection-overlay');
  if(existingOverlay){
    existingOverlay.remove();
  }

  const duration = getAudioElementDurationOrDurationProperty(audioElement, parentNode)
  if(!duration || duration===0){
    return;
  }
  
  //add color mapping

  const detectionOverlay = document.createElement('div');
  detectionOverlay.className = 'bw-player__detection-overlay';

  // get color for rectangle
  const colors = ['rgba(255, 0, 0, 0.4)',
    ' rgba(255, 123, 0, 0.4)',
      'rgba(0, 132, 255, 0.4)',
      'rgba(225, 0, 255, 0.4)',
      'rgba(255, 0, 157, 0.4)'];
  
  const classColorMap = {};
  detectionData.fsdsinet_detected_class.forEach((className, index) => {
    classColorMap[className] = colors[index % colors.length];
  });

  //create rectangles for detection
  detectionData.fsdsinet_detections.forEach((detection,index) => {
    const rect = document.createElement('div');
    rect.className = 'bw-player__detection-rect';

    const left = (detection.start_time / duration) * 100;
    const width = ((detection.end_time-detection.start_time) / duration) * 100;

    const backgroundColor = classColorMap[detection.name];
    const borderColor = backgroundColor.replace('0.4)','1)');

    const numLevels = 5;
    const bottomOffset = 50;
    const availableHeight = 100 - bottomOffset
    const levelHeight = availableHeight/numLevels;
    const level = detection.level;
    const topPercent = level * levelHeight

    const borderOptions = ['solid','dashed']
    const borderWidthOptions = ['3px','2px','1px']
    
    const getBorderStyle = (confidence) => {
      if (confidence >= 0.8) return borderOptions[0]; 
      return borderOptions[1];                        
    };

    const getBorderWidth = (confidence) => {
      if (confidence >= 0.9) return borderWidthOptions[0];
      if (confidence >= 0.8) return borderWidthOptions[1];
      return borderWidthOptions[2];
    }
    
    const borderStyle = getBorderStyle(detection.confidence);
    const borderWidth = getBorderWidth(detection.confidence);

    rect.style.setProperty('--left', `${left}%`);
    rect.style.setProperty('--width', `${Math.max(width, 0.5)}%`);
    rect.style.setProperty('--top', `${topPercent}%`);
    rect.style.setProperty('--height', `${levelHeight - 2}%`);
    rect.style.setProperty('--background', backgroundColor);
    rect.style.setProperty('--border-color', borderColor);
    rect.style.setProperty('--border-style', borderStyle);
    rect.style.setProperty('--border-width', borderWidth);

    rect.setAttribute('role', 'region'); 
    rect.setAttribute('aria-label', 
      `Audio detection of ${detection.name} from ${detection.start_time} to ${detection.end_time} seconds with ${Math.round(detection.confidence * 100)}% confidence. Click to play.`
    );
    rect.setAttribute('title', 
    `Class: ${detection.name}\nTime: ${detection.start_time}s - ${detection.end_time}s\nConfidence: ${Math.round(detection.confidence * 100)}%\nClick to play.`
  );

    const confidence = Math.round(detection.confidence * 100);
    if (width > 0.5) {
      const fullText = `${detection.name} ${confidence}%`;
      const confidenceText = `${confidence}%`

      const measureTextWidth = (text) => {
        const tempElement = document.createElement('span');
        tempElement.className = 'bw-player__text-measure';
        tempElement.textContent = text;
        document.body.appendChild(tempElement);
        const textWidth = tempElement.offsetWidth;
        document.body.removeChild(tempElement);
        return textWidth
      };

      const rectWidth = (width/100)*progressIndicatorContainer.offsetWidth;
      const padding = 5;
      const availableWidth = rectWidth-padding;
      
      const fullTextWidth = measureTextWidth(fullText);
      const confidenceWidth = measureTextWidth(confidenceText);

      if (fullTextWidth <= availableWidth){
        rect.innerHTML = fullText;
      } else if (confidenceWidth <= availableWidth){
        rect.innerHTML = confidenceText;
      } else {
        rect.innerHTML = '';
      }
    }

    rect.addEventListener('click',(e) => {
      e.stopPropagation()
      const playTime = detection.start_time;
      if (audioElement.pause) {
        playAtTime(audioElement,playTime);
      } else {
        audioElement.currentTime = playTime;
      }
    });
    detectionOverlay.appendChild(rect);
  });
  progressIndicatorContainer.parentElement.appendChild(detectionOverlay);

  // create a legend to display color-class matches
  let existingLegend = parentNode.querySelector('.bw-player__detection-legend');
  if (existingLegend) existingLegend.remove();

  const legend = document.createElement('div');
  legend.className = 'bw-player__detection-legend';

  if(Object.entries(classColorMap).length === 0){
    const auxMessage = document.createElement('div');
    auxMessage.textContent = 'Note: no detections available for this sound';
    legend.appendChild(auxMessage);
  } else {
    Object.entries(classColorMap).forEach(([label,color]) => {
    const item = document.createElement('div');
    item.style.display = 'flex';
    item.style.alignItems = 'center';

    const circle = document.createElement('div');
    circle.className = 'bw-player__legend-circle';
    circle.style.setProperty('--color', color)
    const labelSpan = document.createElement('span');
    labelSpan.textContent = label;

    item.appendChild(circle);
    item.appendChild(labelSpan);
    legend.appendChild(item);
  });
  }
 
  parentNode.parentElement.appendChild(legend);
};