import {showToast} from "./toast";

const ratingInputs = document.getElementsByClassName('bw-rating__input');

const updateStarIconsClasses = (ratingContainerElement, newRatingValue) => {
  const relatedStarIconElements = ratingContainerElement.getElementsByClassName('bw-icon-star');
  for (let i=0; i<relatedStarIconElements.length; i+=1){
    const starIconElement = relatedStarIconElements[i];

    // Remove the two possible color classes
    starIconElement.classList.remove('text-red');
    starIconElement.classList.remove('text-light-grey');

    // Get the corresponding rating "value" data property from enclosing label
    const {value} = starIconElement.parentNode.dataset;
    if (parseInt(value,10) <= newRatingValue){
      // If value below or equal to  rating, paint it red
      starIconElement.classList.add('text-red');
    } else {
      // Otherwise make it grey
      starIconElement.classList.add('text-light-grey');
    }
  }
};

const handleRatingInput = ratingInput => {
  const {updateStarsColorOnSave} = ratingInput.parentNode.dataset;
  const {rateUrl} = ratingInput.dataset;
  const req = new XMLHttpRequest();
  req.open('GET', rateUrl, true);
  req.onreadystatechange = () => {
    if (req.readyState === 4) {
      if (req.status === 200) {
        if (updateStarsColorOnSave === "true"){
          updateStarIconsClasses(ratingInput.parentNode, ratingInput.value);
        }
        showToast('Your rating has been recorded');
      } else {
        showToast('There were problems entering your rating. Please try again later');
      }
    }
  };
  req.send(null);
};

ratingInputs.forEach(ratingInput => {
  ratingInput.addEventListener('click', () => handleRatingInput(ratingInput))
});
