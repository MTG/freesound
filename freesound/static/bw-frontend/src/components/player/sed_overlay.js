import { getAudioElementDurationOrDurationProperty, playAtTime } from './utils'

export const createDetectionOverlay = (parentNode, audioElement, detectionData, sedExperiment) => {
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
  let classLevels, nextAvailableLevel;

  if (sedExperiment === 2) {
    classLevels = {};
    nextAvailableLevel = 0;
  }

  detectionData.fsdsinet_detected_class.forEach((className, index) => {
    classColorMap[className] = colors[index % colors.length];
    if (sedExperiment === 2) {
      classLevels[className] = nextAvailableLevel++;
    }
  });

  if (sedExperiment === 1) {
    sedClassWise(detectionData.fsdsinet_detections, duration, classColorMap, progressIndicatorContainer, detectionOverlay, audioElement);
  } else if (sedExperiment === 2) {
    sedLevelWise(detectionData.fsdsinet_detections, duration, classColorMap, progressIndicatorContainer, detectionOverlay, audioElement, classLevels);
  } else if (sedExperiment === 3) {
    sedOnsets(detectionData.fsdsinet_detections, duration, classColorMap, detectionOverlay, audioElement);
  }
  
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

const sedClassWise = (detections, duration, classColorMap, progressIndicatorContainer, detectionOverlay, audioElement) => {
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

  detections.forEach((detection) => {
    const rect = document.createElement('div');
    rect.className = 'bw-player__detection-rect-base bw-player__detection-rect-class';

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
}

const sedLevelWise = (detections, duration, classColorMap, progressIndicatorContainer, detectionOverlay, audioElement, classLevels) => {
  const borderOptions = ['solid','dashed', 'dotted']
  const borderWidthOptions = ['3px','2px']

  // insert labels just once per level (and class)
  const insertedLabels = new Set();
    const getBorderStyle = (confidence) => {
    if (confidence >= 0.8) return borderOptions[0]; //solid
    if (confidence >=0.6) return borderOptions[1]; //dashed
    return borderOptions[2]; //dotted                        
  };

  const getBorderWidth = (confidence) => {
    if (confidence >= 0.9) return borderWidthOptions[0]; //3px borders
    return borderWidthOptions[1]; //2px borders
  }
  
  const wrappers = {}
  //create rectangles for detection
  detections.forEach((detection) => {
    const rect = document.createElement('div');
    rect.className = 'bw-player__detection-rect-base bw-player__detection-rect-level';

    const left = (detection.start_time / duration) * 100;
    const width = ((detection.end_time-detection.start_time) / duration) * 100;

    const backgroundColor = classColorMap[detection.name];
    const borderColor = backgroundColor.replace('0.4)','1)');

    const numLevels = Object.keys(classLevels).length;
    const auxLevels = numLevels > 4 ? 10 : 20; 
    const bottomOffset = 100 - Math.max(0, numLevels) * auxLevels;
    const availableHeight = 100 - bottomOffset
    const levelHeight = availableHeight/numLevels;
    const level = classLevels[detection.name]
    const topPercent = level * levelHeight

    if(!insertedLabels.has(detection.name)){
      insertedLabels.add(detection.name);

      const wrapper = document.createElement('div');
      wrapper.className = 'bw-player__detections-wrapper'
      wrapper.style.setProperty('--top-percent',`${topPercent}%`);
      wrapper.style.setProperty('--level-height',`${levelHeight}%`);

      const label = document.createElement('div');
      label.className = 'bw-player__detection-level-label';
      label.style.flexShrink = 0;
      label.textContent = detection.name;
      wrapper.appendChild(label)

      detectionOverlay.appendChild(wrapper);
      wrappers[detection.name] = wrapper;
    }
    
    const borderStyle = getBorderStyle(detection.confidence);
    const borderWidth = getBorderWidth(detection.confidence);

    rect.style.setProperty('--left', `${left}%`);
    rect.style.setProperty('--width', `${Math.max(width, 0.5)}%`);
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
      //const fullText = `${detection.name} ${confidence}%`;
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
      
      //const fullTextWidth = measureTextWidth(fullText);
      const confidenceWidth = measureTextWidth(confidenceText);

      if (confidenceWidth <= availableWidth){
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
    //detectionOverlay.appendChild(rect);
    wrappers[detection.name].appendChild(rect);
  });  
}

const sedOnsets = (detections, duration, classColorMap, detectionOverlay, audioElement) => {
  //create rectangles for detection
  const activeDetections = []
  const borderOptions = ['solid','dashed','dotted']
  
  const getBorderStyle = (confidence) => {
    if (confidence >= 0.8) return borderOptions[0]; //solid
    if (confidence >= 0.6) return borderOptions[1]; //dashed
    return borderOptions[2];                        
  };

  detections.forEach((detection) => {
    const onset = document.createElement('div');
    onset.className = 'bw-player__detection-onset';

    const label = document.createElement('div');
    label.className = 'bw-player__detection-onset-label';
    label.textContent = `${detection.name} - ${detection.confidence * 100}%`;
    label.style.fontWeight = 'bold';
    onset.appendChild(label);

    const left = (detection.start_time / duration) * 100;
    onset.style.left= `${left}%`;

    const eventDuration = detection.end_time - detection.start_time;
    const durationWidth = (eventDuration / duration) * 100;

    const backgroundColor = classColorMap[detection.name];
    const borderColor = backgroundColor.replace('0.4)','1)');
    
    const borderStyle = getBorderStyle(detection.confidence);
    const borderWidth = '2px';

    // Improved overlap detection logic
    let overlapCount = 0;

    // Check overlap with all previous detections that are still active
    for (let i = activeDetections.length - 1; i >= 0; i--) {
      const activeDetection = activeDetections[i];
      
      // Remove detections that have ended before this one starts
      if (activeDetection.end_time <= detection.start_time) {
        activeDetections.splice(i, 1);
      } else {
        // This detection overlaps with the current one
        overlapCount++;
      }
    }

    // Add current detection to active list
    activeDetections.push(detection);

    // Calculate height percentage based on overlap count
    let heightPercentage = 0.9 - (overlapCount * 0.1);

    // Ensure minimum height
    heightPercentage = Math.max(heightPercentage, 0.1);

    onset.style.setProperty('--border',`${borderWidth} ${borderStyle} ${borderColor}`)
    onset.style.setProperty('--offset-width', `${borderWidth}`)
    onset.style.setProperty('--border-color', borderColor);
    onset.style.setProperty('--duration-width', `${durationWidth}%`);
    onset.style.setProperty('--height-percentage',heightPercentage);
    
    heightPercentage = 0.9;
    onset.setAttribute('role', 'region'); 
    onset.setAttribute('aria-label', 
      `Audio detection of ${detection.name} from ${detection.start_time} to ${detection.end_time} seconds with ${Math.round(detection.confidence * 100)}% confidence. Click to play.`
    );
    onset.setAttribute('title', 
    `Class: ${detection.name}\nTime: ${detection.start_time}s - ${detection.end_time}s\nConfidence: ${Math.round(detection.confidence * 100)}%\nClick to play.`
  );

    label.addEventListener('click',(e) => {
      e.stopPropagation()
      const playTime = detection.start_time;
      if (audioElement.pause) {
        playAtTime(audioElement,playTime);
      } else {
        audioElement.currentTime = playTime;
      }
    });
    detectionOverlay.appendChild(onset);
  });
}