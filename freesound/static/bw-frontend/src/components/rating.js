import {showToast} from "./toast";

const ratingInputs = document.getElementsByClassName('bw-rating__input');

const halfStarHtml = '<span class="bw-icon-half-star text-red"><span class="path1"></span><span class="path2"></span></span>';
const starHtml = '<span class="bw-icon-star text-red"></span></span>';

const updateStarIconsClasses = (ratingContainerElement, newRatingValue, fillClass) => {
  const newRating = parseFloat(newRatingValue);
  const relatedStarIconElements = ratingContainerElement.querySelectorAll(".bw-icon-star,.bw-icon-half-star");
  for (let i=0; i<relatedStarIconElements.length; i+=1){
    const starIconElement = relatedStarIconElements[i];

    // Remove the two possible color classes
    starIconElement.classList.remove('text-yellow');
    starIconElement.classList.remove('text-red');
    starIconElement.classList.remove('text-light-grey');

    // Get the corresponding rating "value" data property from enclosing label
    const {value} = starIconElement.parentNode.dataset;
    const currentStarHighRating = parseInt(value, 10);
    const currentStarLowRating = currentStarHighRating - 1.0;
    const currentStarHalfRating = (currentStarLowRating + currentStarHighRating) / 2;
    if (currentStarHighRating <= newRating){
      starIconElement.outerHTML = starHtml.replace('text-red', fillClass);
    } else if ((currentStarHalfRating <= newRating) && (newRating < currentStarHighRating)){
      // If value below or equal to  rating, paint it with fill class
      starIconElement.outerHTML = halfStarHtml.replace('text-red', fillClass);
    } else {
      // Otherwise make it grey
      starIconElement.outerHTML = starHtml.replace('text-red', 'text-light-grey');
    }
  }
}

const updateRatingWidgetInSoundPageDescriptionSection = (data) => {
  // We are on sound page, update rating element there if num ratings is enough
  const isSoundsPage = window.location.href.indexOf('/sounds/') > -1;
  if (isSoundsPage) {
    const soundPageInformationElement = document.getElementsByClassName('bw-sound-page__information')[0];
    if (soundPageInformationElement !== undefined){
      const ratingsContainer = soundPageInformationElement.getElementsByClassName('bw-rating__container')[0];
      if (ratingsContainer !== undefined){
        updateStarIconsClasses(ratingsContainer, data.avg_rating/2, 'text-red');
      }
      const ratingsCountElement =soundPageInformationElement.getElementsByClassName('bw-rating__count')[0];
      if (ratingsCountElement !== undefined){
        ratingsCountElement.innerText = data.num_ratings_display;
      }
    }
  }
}

const updateRelatedCountAndAvgIndicators = (data, ratingInput) => {
  const ratingsContainer = ratingInput.parentNode;
  const ratingsCountElement = ratingsContainer.parentNode.getElementsByClassName('bw-rating__count')[0];
  if (ratingsCountElement !== undefined){
    ratingsCountElement.innerText = data.num_ratings_display_short;
  }
  const bwPlayer = ratingsContainer.closest('.bw-player');
  if (bwPlayer !== null) {
    const ratingsAvgElement = bwPlayer.parentNode.getElementsByClassName('bw-rating__avg')[0];
    if (ratingsAvgElement !== undefined){
      ratingsAvgElement.innerText = `${(data.avg_rating/2).toFixed(1)}`;
      ratingsAvgElement.title = data.num_ratings_display;
    }
  }
}

const handleRatingInput = ratingInput => {
  showToast('Rating sound...');
  const {showAddedRatingOnSave} = ratingInput.parentNode.dataset;
  const {rateUrl} = ratingInput.dataset;
  const req = new XMLHttpRequest();
  req.open('GET', rateUrl, true);
  req.onreadystatechange = () => {
    if (req.readyState === 4) {
      if (req.status === 200) {
        const data = JSON.parse(req.responseText);
        if (data.success) {
          if (showAddedRatingOnSave === "true"){
            // Keep the added rating in the stars widget
            updateStarIconsClasses(ratingInput.parentNode, ratingInput.value, 'text-yellow');
          } else {
            // Update the stars widget to reflect the new average rating (only if num ratings above minimum)
            if (data.num_ratings >= data.min_num_ratings) {
              updateStarIconsClasses(ratingInput.parentNode, data.avg_rating/2, 'text-red');
            }
          }
          if (data.num_ratings >= data.min_num_ratings) {
            // Update related count and avg indicators (if any)
            updateRelatedCountAndAvgIndicators(data, ratingInput);
            
            // Update related rating widget and count indicator in sound information section (only applies to sound page)
            updateRatingWidgetInSoundPageDescriptionSection(data);
          }
        }
        showToast(data.message);
      } else {
        showToast('There were problems entering your rating. Please try again later');
      }
    }
  };
  req.send(null);
};


const addRatingInputEventListeners = inputs => {
  inputs.forEach(ratingInput => {
    ratingInput.addEventListener('click', evt => {
      handleRatingInput(ratingInput);
      evt.stopPropagation();
    })
  });
}


addRatingInputEventListeners(ratingInputs)

