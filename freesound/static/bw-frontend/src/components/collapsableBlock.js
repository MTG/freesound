const collapsableText = document.getElementById('collapsable-text');

const handleCollapsable = () => {
  const collapsableContainer = document.getElementById(collapsableText.dataset.target);

  console.log(collapsableContainer)
  collapsableContainer.classList.toggle('collapsable-block-close');
  const showText = collapsableText.dataset.showText;
  const hideText = collapsableText.dataset.hideText;
  collapsableText.textContent = collapsableText.textContent.includes(showText)
    ? hideText
    : showText;
};

if (collapsableText !== null){
  collapsableText.addEventListener('click', handleCollapsable);
}

