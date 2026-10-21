import postcssMixins from 'postcss-mixins';

// Миксины типографики дизайн-системы (@define-mixin из vars/typography.css).
// @import в CSS Vite разворачивает сам (встроенный postcss-import), до этого плагина.
export default {
  plugins: [postcssMixins()],
};
