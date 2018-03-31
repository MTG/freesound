export const getIcon = iconName => {
  // first get the icon plain text
  const iconTextContent = require(`../../styles/assets/icons/${iconName}.svg`);
  // then convert it to an svg node
  const iconSvgNode = document.createRange().createContextualFragment(iconTextContent);
  return iconSvgNode;
};
