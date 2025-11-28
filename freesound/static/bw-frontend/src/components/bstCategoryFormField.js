const updateSubcategoriesList = (
  hiddenField,
  subcategoryContainer,
  subcategoryButtons
) => {
  if (hiddenField.value === '') {
    subcategoryContainer.classList.add('display-none');
    return;
  } else {
    // Display subcategories that match the selected top-level category
    // Triggered when a selection is made or updated.
    const correspondingTopLevelValue = hiddenField.value.split('-')[0]; // Extract top-level value, if not already.
    if (correspondingTopLevelValue) {
      subcategoryContainer.classList.remove('display-none');
      subcategoryButtons.forEach(subBtn => {
        const topLevelValue = subBtn.getAttribute('top_level');
        subBtn.style.display =
          topLevelValue === correspondingTopLevelValue
            ? 'inline-block'
            : 'none';
      });
    }
  }
};

const prepareCategoryFormFields = mainContainer => {
  const categoryFieldContainers =
    mainContainer.getElementsByClassName('bst-category-field');
  categoryFieldContainers.forEach(container => {
    const hiddenField = container.querySelectorAll('input[type=hidden]')[0];
    const topButtons = container.querySelectorAll('.top-buttons .btn');
    const subcategoryContainer = container.querySelector(
      '.subcategory-buttons'
    );
    const subcategoryButtons =
      subcategoryContainer.querySelectorAll('.btn-subcategory');

    // Event listener for top-level category buttons
    topButtons.forEach(topBtn => {
      topBtn.addEventListener('click', function () {
        const selectedValue = this.getAttribute('data_value');

        // Update hidden input value
        hiddenField.value = selectedValue;

        // Highlight the selected top-level category button
        topButtons.forEach(btn => {
          btn.classList.remove('btn-primary');
          btn.classList.add('btn-inverse');
          btn.setAttribute('aria-selected', 'false');
        });
        this.classList.remove('btn-inverse');
        this.classList.add('btn-primary');
        this.setAttribute('aria-selected', 'true');

        updateSubcategoriesList(
          hiddenField,
          subcategoryContainer,
          subcategoryButtons
        );
      });
    });

    // Event listener for subcategory buttons
    subcategoryButtons.forEach(subBtn => {
      subBtn.addEventListener('click', function () {
        const subcategoryValue = this.getAttribute('data_value');

        // Update hidden input value if subcategory is clicked
        hiddenField.value = subcategoryValue;

        // Highlight the selected subcategory button
        subcategoryButtons.forEach(btn => {
          btn.classList.remove('btn-primary');
          btn.classList.add('btn-inverse');
          btn.setAttribute('aria-selected', 'false');
        });
        this.classList.remove('btn-inverse');
        this.classList.add('btn-primary');
        this.setAttribute('aria-selected', 'true');
      });
    });

    updateSubcategoriesList(
      hiddenField,
      subcategoryContainer,
      subcategoryButtons
    );
  });
};

export { prepareCategoryFormFields };
