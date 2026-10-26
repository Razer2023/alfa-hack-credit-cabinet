import postcssMixins from 'postcss-mixins';

// Тёмная тема дизайн-системы (themes/dark.css) объявлена на :root и включилась бы всегда.
// Переносим её на :root[data-theme="dark"], чтобы тему можно было переключать (src/theme.tsx).
const scopeDarkTheme = () => ({
  postcssPlugin: 'scope-dark-theme',
  Once(root) {
    root.walkRules((rule) => {
      const file = (rule.source?.input.file ?? '').replace(/\\/g, '/');
      if (file.endsWith('core-components-themes/dark.css') && rule.selector.trim() === ':root') {
        rule.selector = ':root[data-theme="dark"]';
      }
    });
  },
});
scopeDarkTheme.postcss = true;

// Миксины типографики дизайн-системы (@define-mixin из vars/typography.css).
// @import в CSS Vite разворачивает сам (встроенный postcss-import), до этих плагинов.
export default {
  plugins: [scopeDarkTheme(), postcssMixins()],
};
