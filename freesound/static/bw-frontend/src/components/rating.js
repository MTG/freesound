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
};

const updateRatingWidgetInSoundPageDescriptionSection = (data) => {
  if (data.num_ratings >= data.min_num_ratings) {
    const soundPageInformationElement = document.getElementsByClassName('bw-sound-page__information')[0];
    if (soundPageInformationElement !== undefined){
      // We are on sound page, update rating element there if num ratings is enough
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

const handleRatingInput = ratingInput => {
  showToast('Rating sound...');
  const {updateStarsColorOnSave} = ratingInput.parentNode.dataset;
  const {rateUrl} = ratingInput.dataset;
  const req = new XMLHttpRequest();
  req.open('GET', rateUrl, true);
  req.onreadystatechange = () => {
    if (req.readyState === 4) {
      if (req.status === 200) {
        if (updateStarsColorOnSave === "true"){
          updateStarIconsClasses(ratingInput.parentNode, ratingInput.value, 'text-yellow');
        }
        const data = JSON.parse(req.responseText);
        updateRatingWidgetInSoundPageDescriptionSection(data);
        showToast('Your rating has been recorded!');
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

