// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

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

// @license-end
