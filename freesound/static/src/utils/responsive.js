const xl = '(min-width: 1200px)';
const lg = '(min-width: 992px)';
const md = '(min-width: 768px)';
const sm = '(min-width: 576px)';

export const getCurrentSize = () => {
  switch (true) {
    case window.matchMedia(xl).matches:
      return 'xl';
    case window.matchMedia(lg).matches:
      return 'lg';
    case window.matchMedia(md).matches:
      return 'md';
    case window.matchMedia(sm).matches:
      return 'sm';
    default:
      return 'xs';
  }
};

export const isMobile = () => ['xs', 'sm'].includes(getCurrentSize());
