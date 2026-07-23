export const setURLHash = newHash => {
  location.hash = newHash;
};

export const hashEquals = hash => {
  if (!hash.startsWith('#')) {
    hash = '#' + hash;
  }
  return location.hash == hash;
};
