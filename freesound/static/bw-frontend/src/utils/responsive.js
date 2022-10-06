// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

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

// @license-end
