const ratingInputs = document.getElementsByClassName('bw-rating__input');

const handleRatingInput = ratingInput => {
  console.log('handleRating', ratingInput);

  // handle rating request
};

ratingInputs.forEach(ratingInput =>
  ratingInput.addEventListener('click', () => handleRatingInput(ratingInput))
);
