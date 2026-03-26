export const createIconElement = iconName => {
  const node = document.createElement('i');
  node.classList.add(iconName);
  return node;
};
