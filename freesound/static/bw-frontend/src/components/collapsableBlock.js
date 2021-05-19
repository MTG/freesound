const collapsableText = document.getElementById('collapsable-text');

const handleCollapsable = () => {
  const collapsableContainer = document.getElementById(collapsableText.dataset.target);

  collapsableContainer.classList.toggle('collapsable-block-close');
  collapsableText.textContent = collapsableText.textContent.includes('Show more')
    ? 'Show less'
    : 'Show more';
};

collapsableText.addEventListener('click', handleCollapsable);
